standardize_parser.add_argument("--libraries-dir", default="../libraries", help="Path to the libraries directory")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a PSC JSON file")
    validate_parser.add_argument("--input-file", required=True, help="Path to the input PSC JSON file")
    validate_parser.add_argument("--output-file", help="Path to save the validation report (optional)")
    validate_parser.add_argument("--libraries-dir", default="../libraries", help="Path to the libraries directory")
    
    # Generate code command
    generate_parser = subparsers.add_parser("generate-code", help="Generate DreamBot Java code from a PSC JSON file")
    generate_parser.add_argument("--input-file", required=True, help="Path to the input PSC JSON file")
    generate_parser.add_argument("--output-file", required=True, help="Path to save the generated Java code")
    generate_parser.add_argument("--libraries-dir", default="../libraries", help="Path to the libraries directory")
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "analyze":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.analyze_psc_json(args.input_file, args.output_file)
    
    elif args.command == "standardize":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.standardize_psc_json(args.input_file, args.output_file)
    
    elif args.command == "validate":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.validate_psc_json(args.input_file, args.output_file)
    
    elif args.command == "generate-code":
        standardizer = PSCStandardizer(args.libraries_dir)
        standardizer.generate_dreambot_code(args.input_file, args.output_file)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
