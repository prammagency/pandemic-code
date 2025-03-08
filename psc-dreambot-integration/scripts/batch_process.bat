@echo off
:: Batch processing script for PSC JSON files

:: Default settings - use parent directory paths
set SCRIPT_DIR=%~dp0
set PARENT_DIR=%SCRIPT_DIR%..
set RAW_DIR=%PARENT_DIR%\data\raw
set ORGANIZED_DIR=%PARENT_DIR%\data\organized
set STD_DIR=%PARENT_DIR%\data\standardized
set ANALYSIS_DIR=%PARENT_DIR%\data\analysis
set VALIDATION_DIR=%PARENT_DIR%\data\validation
set JAVA_DIR=%PARENT_DIR%\output\java
set CATEGORY_MAP=%PARENT_DIR%\mapping\ActionID_CategoryMap.json
set LIBRARIES_DIR=%PARENT_DIR%\libraries

:: Parse command line arguments
set ORGANIZE=true
set ANALYZE=true
set STANDARDIZE=true
set VALIDATE=true
set GENERATE=true
set SPECIFIC_CATEGORY=
set SPECIFIC_FILE=

:parse_args
if "%~1"=="" goto end_parse_args
if "%~1"=="--raw-dir" (
    set RAW_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--organized-dir" (
    set ORGANIZED_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--std-dir" (
    set STD_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--analysis-dir" (
    set ANALYSIS_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--validation-dir" (
    set VALIDATION_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--java-dir" (
    set JAVA_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--category-map" (
    set CATEGORY_MAP=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--libraries-dir" (
    set LIBRARIES_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--organize-only" (
    set ANALYZE=false
    set STANDARDIZE=false
    set VALIDATE=false
    set GENERATE=false
    shift
    goto parse_args
)
if "%~1"=="--analyze-only" (
    set ORGANIZE=false
    set STANDARDIZE=false
    set VALIDATE=false
    set GENERATE=false
    shift
    goto parse_args
)
if "%~1"=="--standardize-only" (
    set ORGANIZE=false
    set ANALYZE=false
    set VALIDATE=false
    set GENERATE=false
    shift
    goto parse_args
)
if "%~1"=="--validate-only" (
    set ORGANIZE=false
    set ANALYZE=false
    set STANDARDIZE=false
    set GENERATE=false
    shift
    goto parse_args
)
if "%~1"=="--generate-only" (
    set ORGANIZE=false
    set ANALYZE=false
    set STANDARDIZE=false
    set VALIDATE=false
    shift
    goto parse_args
)
if "%~1"=="--category" (
    set SPECIFIC_CATEGORY=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--file" (
    set SPECIFIC_FILE=%~2
    shift
    shift
    goto parse_args
)
shift
goto parse_args
:end_parse_args

:: Create necessary directories
if not exist "%ORGANIZED_DIR%" mkdir "%ORGANIZED_DIR%"
if not exist "%STD_DIR%" mkdir "%STD_DIR%"
if not exist "%ANALYSIS_DIR%" mkdir "%ANALYSIS_DIR%"
if not exist "%VALIDATION_DIR%" mkdir "%VALIDATION_DIR%"
if not exist "%JAVA_DIR%" mkdir "%JAVA_DIR%"

:: Check that the category map exists
if not exist "%CATEGORY_MAP%" (
    echo Error: Category map file does not exist: %CATEGORY_MAP%
    exit /b 1
)

:: Step 1: Organize files
if "%ORGANIZE%"=="true" if "%SPECIFIC_FILE%"=="" (
    echo Step 1: Organizing PSC JSON files...
    python organize_psc_files.py --source-dir "%RAW_DIR%" --target-dir "%ORGANIZED_DIR%" --category-map "%CATEGORY_MAP%" --generate-report
    
    if errorlevel 1 (
        echo Error: Organization step failed.
        exit /b 1
    )
    echo Organization complete.
)

:: Determine which files to process
set FILES=
if not "%SPECIFIC_FILE%"=="" (
    if "%ORGANIZE%"=="true" (
        set FILES=%RAW_DIR%\%SPECIFIC_FILE%
    ) else (
        for /r "%ORGANIZED_DIR%" %%f in (*%SPECIFIC_FILE%) do set FILES=%%f
    )
) else if not "%SPECIFIC_CATEGORY%"=="" (
    set FILES=%ORGANIZED_DIR%\%SPECIFIC_CATEGORY%\*.json
) else (
    set FILES=%ORGANIZED_DIR%\*\*.json
)

:: Process each file
for %%f in (%FILES%) do (
    if exist "%%f" (
        set file=%%f
        
        :: Get filename and category
        for %%i in ("%%f") do set filename=%%~nxi
        for %%i in ("%%~dpf\.") do set category=%%~nxi
        
        echo Processing %category%\%filename%
        
        :: Step 2: Analyze
        if "%ANALYZE%"=="true" (
            echo   Analyzing...
            python psc_standardizer.py analyze --input-file "%%f" --output-file "%ANALYSIS_DIR%\%filename:.json=_analysis.json%"
            
            if errorlevel 1 (
                echo   Warning: Analysis failed for %filename%.
            )
        )
        
        :: Step 3: Standardize
        if "%STANDARDIZE%"=="true" (
            echo   Standardizing...
            set EXTRA_ARGS=
            
            :: Enable game-specific libraries based on category
            if "%category%"=="combat" set EXTRA_ARGS=%EXTRA_ARGS% --use-monster-library
            if "%category%"=="entities_npcs" set EXTRA_ARGS=%EXTRA_ARGS% --use-monster-library
            if "%category%"=="equipment" set EXTRA_ARGS=%EXTRA_ARGS% --use-equipment-library
            if "%category%"=="inventory" set EXTRA_ARGS=%EXTRA_ARGS% --use-equipment-library
            if "%category%"=="walking" set EXTRA_ARGS=%EXTRA_ARGS% --use-location-library
            if "%category%"=="banking" set EXTRA_ARGS=%EXTRA_ARGS% --use-location-library
            
            if not exist "%STD_DIR%\%category%" mkdir "%STD_DIR%\%category%"
            python psc_standardizer.py standardize --input-file "%%f" --output-file "%STD_DIR%\%category%\%filename:.json=_std.json%" %EXTRA_ARGS%
            
            if errorlevel 1 (
                echo   Warning: Standardization failed for %filename%.
                goto next_file
            )
        )
        
        :: Step 4: Validate
        if "%VALIDATE%"=="true" (
            echo   Validating...
            if not exist "%VALIDATION_DIR%\%category%" mkdir "%VALIDATION_DIR%\%category%"
            python psc_standardizer.py validate --input-file "%STD_DIR%\%category%\%filename:.json=_std.json%" --output-file "%VALIDATION_DIR%\%category%\%filename:.json=_validation.json%"
            
            if errorlevel 1 (
                echo   Warning: Validation failed for %filename%.
                goto next_file
            )
        )
        
        :: Step 5: Generate code
        if "%GENERATE%"=="true" (
            echo   Generating Java code...
            if not exist "%JAVA_DIR%\%category%" mkdir "%JAVA_DIR%\%category%"
            
            :: Convert filename to Java class name
            set class_name=%filename:.json=%
            set class_name=%class_name: =%
            set class_name=%class_name:-=%
            set class_name=%class_name:_=%
            
            python psc_standardizer.py generate-code --input-file "%STD_DIR%\%category%\%filename:.json=_std.json%" --output-file "%JAVA_DIR%\%category%\%class_name%.java"
            
            if errorlevel 1 (
                echo   Warning: Code generation failed for %filename%.
                goto next_file
            )
        )
        
        :next_file
    )
)

echo Batch processing complete.
echo Summary:
echo   - Raw directory: %RAW_DIR%
echo   - Organized directory: %ORGANIZED_DIR%
echo   - Standardized directory: %STD_DIR%
echo   - Analysis directory: %ANALYSIS_DIR%
echo   - Validation directory: %VALIDATION_DIR%
echo   - Java code directory: %JAVA_DIR%

echo.
echo Done.