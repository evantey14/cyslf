import argparse

parser = argparse.ArgumentParser(
    description="Process raw registration forms into a standard csv."
)

parser.add_argument(
    "--version", "-v", type=str, help="Get current version."
)

def main():
    print("Version: 0.2.13\nDocumentation: https://github.com/evantey14/cyslf#readme")


if __name__ == "__main__":
    main()
