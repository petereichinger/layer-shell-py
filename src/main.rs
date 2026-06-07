use clap::{CommandFactory, Parser};
use layer_shell_rs::cli::{Cli, run};
use std::process::ExitCode;

fn main() -> ExitCode {
    if std::env::args_os().len() == 1 {
        let mut command = Cli::command();
        command.print_help().expect("help text should render");
        println!();
        return ExitCode::SUCCESS;
    }

    let cli = Cli::parse();

    match run(cli) {
        Ok(code) => ExitCode::from(code.clamp(0, u8::MAX as i32) as u8),
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
