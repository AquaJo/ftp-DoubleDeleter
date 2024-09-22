# xclip is required!

from ftplib import FTP
import subprocess
import re

def normalize_ftp_dir(path):
    if not path.startswith('/'):
        path = '/' + path

    if path.endswith('/'):
        path = path[:-1]
    
    return path


# FTP-Details needed for connection
ftp_host = input("Please enter the FTP host: ")
ftp_user = input("Please enter the FTP username: ")
ftp_pass = input("Please enter the FTP password: ")

# FTP-Directory you want to delete ._ files from
ftp_dir = normalize_ftp_dir(input("Please enter the FTP dir (from *Your* FTP-Root) you want to delete ._ files from: "))

# Location of the log file containing a js array of the files to delete (leave it "")
logFile_location = input("Please enter the relative folder-location of the log file (leave empty if you don't want to): ")


# Create a list to store files to be deleted
files_to_delete = []
def list_items(ftp, path):
    ftp.cwd(path)
    items = []
    ftp.retrlines("LIST -a", items.append)  # Holen der Liste aller Dateien und Verzeichnisse

    result = []

    for entry in items:
        parts = re.split(r'\s+', entry, 8)  # Aufteilen der Ausgabe in Teile
        name = parts[-1]  # Der Dateiname ist der letzte Teil
        file_type = parts[0][0]  # Der erste Buchstabe der Berechtigungen zeigt den Typ an

        # Überspringe '.' und '..'
        if name in ['.', '..'] or name.startswith('.__'): # in case there is a .__ file type existing in the world, skip it for safety
            continue

        # Is it a directory? (true für 'd', false für '-')
        is_dir = file_type == 'd'
        is_file = file_type == '-'
        # Use object structure to store the file/ folder data
        result.append({
            'isDir': is_dir,
            'isFile': is_file,
            'name': name
        })

    return result

def copy_to_clipboard(text):
    try:
        process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
        process.communicate(input=text.encode('utf-8'))
    except Exception as e:
        print(f"Failed to copy to clipboard: {e}")

def list_delete_files_recursively(ftp, path):
    # Ensure you start from the correct directory
    print(f"Changed directory (to be tested) to: {path}")
    # List files and directories in the current path
    try:
       items = list_items(ftp, path)
       for item in items:
        full_item_path = f"{path}/{item['name']}"  # Create full path for the item
        if item['isDir']:
            # Try changing to the subdirectory
            ftp.cwd(full_item_path)  # If successful, it's a directory
            # Recursive call for the subdirectory
            list_delete_files_recursively(ftp, f"{full_item_path}")
            # Go back to the parent directory after processing the subdirectory
            ftp.cwd(path)  # Reset to the original path
        elif item['isFile']:
            # If it's not a directory, check if the file starts with '._'
            if item['name'].startswith("._"):
                print(f"Marking for deletion: {full_item_path}")
                files_to_delete.append(full_item_path)  # Add file to the list
    except Exception as e:
        print(f"Failed to list items in {path}: {e}")
        return

# Try to establish the FTP connection
try:
    ftp = FTP(ftp_host)
    ftp.login(user=ftp_user, passwd=ftp_pass)
    print("Connected to FTP server successfully.")


    # Start the recursive deletion process
    list_delete_files_recursively(ftp, ftp_dir)

    # If there are files to delete, ask for confirmation
    if files_to_delete:
        print("The following files will be deleted:")
        for file in files_to_delete:
            print(f"- {file}")
        # Format the list as a JavaScript array
        js_array = "const filesToDelete = [\n" + ",\n".join(f'  "{file}"' for file in files_to_delete) + "\n];"
        # Copy the JavaScript array to the clipboard
        copy_to_clipboard(js_array)
        print("Copied the list of files to delete to the clipboard as JavaScript array.")

        if not logFile_location:
            logFile_location = 'files_to_delete.js'
        with open(logFile_location, 'w') as js_file:
            js_file.write(js_array)
        print(f"Wrote the list of files to delete to {logFile_location}.")

        confirm = input(f"Do you really want to delete these files ({len(files_to_delete)} files)? (yes/no): ").strip().lower()
    
        if confirm == 'yes':
            for file in files_to_delete:
                ftp.delete(file)
                print(f"File deleted: {file}")
        else:
            print("Deletion process canceled.")
    else:
        print("No files to delete found.")

    # Close the FTP connection
    ftp.quit()
except Exception as e:
    print(f"Failed to connect to FTP server: {e}")
    exit()  # Exit the script if the connection fails