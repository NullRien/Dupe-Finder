import os
import sys
import hashlib
from tinydb import TinyDB, Query, where
from time import sleep
import json

#add option to crawl subfolders later


def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    BUF_SIZE = 65536
    folderpath = input("Enter the path of the folder to check: ")
    def buffer_size():
        BUF_SIZE = input("Enter the buffer size (press enter for default 65536KB): ")
    buffer_size()
    if isinstance(BUF_SIZE, int):
        hashfile(folderpath, BUF_SIZE)
    elif BUF_SIZE == "":
        BUF_SIZE = 65536
        hashfile(folderpath, BUF_SIZE)
    else:
        print("Error: Buffer size must be an integer")
        sleep(2)
        os.system('cls' if os.name == 'nt' else 'clear')
        buffer_size()


def hashfile(folderpath, BUF_SIZE):
    files = []
    safefiles = {}
    removefiles = {}
    dupedfiles = 0
    try:
        os.walk(folderpath)
    except:
        print("Error: Invalid path")
        sleep(2)
        os.system('cls' if os.name == 'nt' else 'clear')
        main()

    for r, d, f in os.walk(folderpath):
        for file in f:
            files.append(os.path.join(r, file))

    try:
        for f in files:
            md5 = hashlib.md5()
            with open(f, 'rb') as file:
                while True:
                    data = file.read(BUF_SIZE)
                    if not data:
                        break
                    md5.update(data)
                if md5.hexdigest() in safefiles:
                    dupedfiles += 1
                    removefiles[f] = md5.hexdigest()
                else:
                    safefiles[md5.hexdigest()] = f

        print("Found "+ str(dupedfiles) + " duplicate files.")
        if dupedfiles > 0:
            if input("Do you want to delete these files? (y/n): ") == "y":
                for f in removefiles:
                    os.remove(f)
                input("Removed " + str(dupedfiles) + " files. Press enter to exit.")
                sys.exit()
            else:
                input("Press enter to exit")
                sys.exit()

    except Exception as e:
        with open('error.log', 'a') as error:
            error.write(str(e) + "\n")
            error.close()


main()