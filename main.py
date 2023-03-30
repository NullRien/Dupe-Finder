from os import system, name, walk, remove, path
from sys import exit
from hashlib import md5
from time import sleep
md5 = md5()

#add option to crawl subfolders later


def main():
    system('cls' if name == 'nt' else 'clear')
    BUF_SIZE = 65536
    folderpath = input("Enter the path of the folder to check: ")
    usebuffer = input("Do you want to use buffering? (helps with large files and speed) (y/n): ")
    if usebuffer == "y":
        buffer_size()
    else:
        hashfile(folderpath, False)
    def buffer_size():
        BUF_SIZE = input("Enter the buffer size (press enter for default 65536KB): ")
    if isinstance(BUF_SIZE, int):
        hashfile(folderpath, BUF_SIZE)
    elif BUF_SIZE == "":
        BUF_SIZE = 65536
        hashfile(folderpath, BUF_SIZE)
    else:
        print("Error: Buffer size must be an integer")
        sleep(2)
        system('cls' if name == 'nt' else 'clear')
        buffer_size()


def hashfile(folderpath, BUF_SIZE):
    files = []
    safefiles = {}
    removefiles = {}
    dupedfiles = 0
    try:
        walk(folderpath)
    except:
        print("Error: Invalid path")
        sleep(2)
        system('cls' if name == 'nt' else 'clear')
        main()

    for r, d, f in walk(folderpath):
        for file in f:
            files.append(path.join(r, file))

    try:
        for f in files:
            with open(f, 'rb') as file:
                while True:
                    if BUF_SIZE == False:
                        data = file.read()
                    else:
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
                    remove(f)
                input("Removed " + str(dupedfiles) + " files. Press enter to exit.")
                exit()
            else:
                input("Press enter to exit")
                exit()
        else:
            input("No duplicate files found. Press enter to exit.")
            exit()

    except Exception as e:
        with open('error.log', 'a') as error:
            error.write(str(e) + "\n")
            error.close()


main()