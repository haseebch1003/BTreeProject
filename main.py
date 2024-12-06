import os

BLOCK_SIZE = 512
HEADER_SIZE = 24
MAGIC_HEADER = b"FILEHDR1"


class GeneralFile:
    def __init__(self):
        self.file = None
        self.open_file_name = None

    def create_new_file(self, file_name):
        if os.path.exists(file_name):
            overwrite = input(f"{file_name} already exists. Overwrite? (yes/no): ").strip().lower()
            if overwrite != "yes":
                print("File creation canceled.")
                return
        with open(file_name, "wb") as f:
            header = MAGIC_HEADER + (0).to_bytes(8, "big") + (1).to_bytes(8, "big")
            f.write(header.ljust(BLOCK_SIZE, b'\x00'))
        print(f"{file_name} created.")
        self.open_file_name = file_name

    def open_existing_file(self, file_name):
        if not os.path.exists(file_name):
            print(f"Error: {file_name} does not exist.")
            return
        with open(file_name, "rb") as f:
            header = f.read(HEADER_SIZE)
            if header[:8] != MAGIC_HEADER:
                print(f"Error: {file_name} is not a valid file.")
                return
        self.file = open(file_name, "r+b")
        self.open_file_name = file_name
        print(f"{file_name} opened.")

    def close_file(self):
        if self.file:
            self.file.close()
            self.file = None
            print("File closed.")


def main():
    file_handler = GeneralFile()
    while True:
        print("\nOptions: create, open, quit")
        choice = input("Select an option: ").strip().lower()
        if choice == "create":
            name = input("Enter file name: ").strip()
            file_handler.create_new_file(name)
        elif choice == "open":
            name = input("Enter file name: ").strip()
            file_handler.open_existing_file(name)
        elif choice == "quit":
            file_handler.close_file()
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()

