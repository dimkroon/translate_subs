"""
Safely make I/O operations to files in Python even from multiple threads... and more!

© Anime no Sekai — 2020
"""
from math import sqrt
from time import sleep
from json import loads, dumps
from collections import Counter
from threading import Thread, Lock
from os import rename, remove, replace
from os.path import isfile, getsize, exists


class OverwriteError(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super(OverwriteError, self).__init__(message)


def stringSimilarity(string1, string2):
    """
    Returns the similarity bewteen two strings
    """

    def get_vector(word):
        count_characters = Counter(word)
        set_characters = set(count_characters)
        length = sqrt(sum(c * c for c in count_characters.values()))
        return count_characters, set_characters, length, word

    vector1 = get_vector(string1)
    vector2 = get_vector(string2)
    common_characters = vector1[1].intersection(vector2[1])
    product_summation = sum(vector1[0][character] * vector2[0][character] for character in common_characters)
    length = vector1[2] * vector2[2]
    return (0 if length == 0 else (1 if product_summation / length > 1 else product_summation / length))


class TextFile():
    """
    A Text File object
    """

    def __init__(self, filepath, encoding="utf-8", blocking=True) -> None:
        self.filepath = str(filepath)
        self.encoding = str(encoding)
        self.blocking = (True if str(blocking).lower().replace(" ", "") in ["true", "yes", "1"] else False)
        self._blocking = blocking
        self._currentOperation = 1
        self._queueLength = 0
        self._Lock = Lock()

    def __repr__(self) -> str:
        """
        Representing the object -> str FileType: filepath
        """
        return "TextFile: " + self.filepath

    def __str__(self) -> str:
        """
        String representation of the object -> str filepath
        """
        return self.filepath

    def __sub__(self, other):
        """
        Substract two safeIO objects

        Returns the Cosine Similarity of the two objects (float [0;1]) if they are both instances of safeIO.TextFile or safeIO.JSONFile\n
        Returns the difference in size between the two files if one of them is a BinaryFile instance\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            result = stringSimilarity(self.read(), other.read())
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        elif isinstance(other, BinaryFile):
            return getsize(self.filepath) - getsize(other.filepath)
        else:
            return None

    def __eq__(self, other):
        """
        Checks for an equality between two safeIO objects (==)

        Returns True if the contents of the two files are the same\n
        Returns False else\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            if self.read() == other.read():
                result = True
            else:
                result = False
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        else:
            return None

    def __ne__(self, other):
        """
        Checks for an inequality between two safeIO objects (!=)

        Returns False if the contents of the two files are the same\n
        Returns True else\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            if self.read() == other.read():
                result = False
            else:
                result = True
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        else:
            return None

    def __iter__(self):
        """
        Returns self.readlines() iterator
        """
        return self.readlines().__iter__()

    def __enter__(self):
        """
        'with' statement handling
        """
        self._blocking = self.blocking
        self.blocking = True
        return self

    def __exit__(self, type, value, traceback):
        """
        Exit of 'with' statement (deleting the file)
        """
        self.blocking = self._blocking

    def isfile(self, callback=None):
        """
        Wether the file exists on the disk or not
        """
        self._Lock.acquire()

        def _isfile(callback=None):
            """
            Internal name() function
            """
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            data = isfile(self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _isfile()
        else:
            Thread(target=_isfile, args=[callback], daemon=True).start()

    def delete(self, callback=None):
        """
        Deletes the file
        """
        self._Lock.acquire()

        def _delete(callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            remove(self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _delete()
        else:
            Thread(target=_delete, args=[callback], daemon=True).start()

    def rename(self, newName, overwrite=False, callback=None):
        """
        Renames the file and returns its new path
        """
        self._Lock.acquire()

        def _rename(newName, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            oldFilepath = self.filepath
            if "/" in self.filepath:
                self.filepath = self.filepath[:self.filepath.rfind("/")] + "/" + newName
            else:
                self.filepath = newName
            while operationID != self._queueLength:
                sleep(0.001)
            if not overwrite:
                if exists(self.filepath):
                    newFilepath = self.filepath
                    self.filepath = oldFilepath
                    raise OverwriteError(newFilepath + " already exists and overwrite=False")
            replace(oldFilepath, self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return self.filepath
            else:
                callback(self.filepath)

        if self.blocking:
            return _rename(newName)
        else:
            Thread(target=_rename, args=[newName, callback], daemon=True).start()

    def move(self, newPath, overwrite=False, callback=None):
        """
        Moves the file and returns its new path
        """
        self._Lock.acquire()

        def _move(newPath, overwrite=False, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            oldFilepath = self.filepath
            self.filepath = newPath
            while operationID != self._queueLength:
                sleep(0.001)
            if not overwrite:
                if exists(self.filepath):
                    newFilepath = self.filepath
                    self.filepath = oldFilepath
                    raise OverwriteError(newFilepath + " already exists and overwrite=False")
            replace(oldFilepath, self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return self.filepath
            else:
                callback(self.filepath)

        if self.blocking:
            return _move(newPath, overwrite)
        else:
            Thread(target=_move, args=[newPath, overwrite, callback], daemon=True).start()

    def name(self, callback=None):
        """
        Returns the file name
        """
        self._Lock.acquire()

        def _name(callback=None):
            """
            Internal name() function
            """
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                data = readingFile.name
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _name()
        else:
            Thread(target=_name, args=[callback], daemon=True).start()

    def fileno(self, callback=None):
        """
        Returns the file descriptor (int) used by Python to request I/O operations from the operating system.
        """
        self._Lock.acquire()

        def _fileno(callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                data = readingFile.fileno()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _fileno()
        else:
            Thread(target=_fileno, args=[callback], daemon=True).start()

    def read(self, position=0, callback=None):
        """
        Reads the entire file and returns its content
        """
        self._Lock.acquire()

        def _read(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            if not isfile(self.filepath):
                open(self.filepath, "w").close()
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                readingFile.seek(int(position))
                data = readingFile.read()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _read(position)
        else:
            Thread(target=_read, args=[position, callback], daemon=True).start()

    def write(self, data, position=0, callback=None):
        """
        Writes (or overwrites) to the file and returns the number of characters written
        """
        self._Lock.acquire()

        def _write(data, position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "w", encoding=self.encoding) as writingFile:
                writingFile.seek(int(position))
                data = writingFile.write(str(data))
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _write(data, position)
        else:
            Thread(target=_write, args=[data, position, callback], daemon=True).start()

    def append(self, data, callback=None):
        """
        Appends to the file and returns the number of characters written
        """
        self._Lock.acquire()

        def _append(data, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "a", encoding=self.encoding) as writingFile:
                data = writingFile.write(str(data))
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _append(data)
        else:
            Thread(target=_append, args=[data, callback], daemon=True).start()

    def readline(self, position=0, callback=None):
        """
        Returns the line of the current position (from the position to the linebreak)
        """
        self._Lock.acquire()

        def _readline(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                readingFile.seek(int(position))
                data = readingFile.readline()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _readline(position)
        else:
            Thread(target=_readline, args=[position, callback], daemon=True).start()

    def readlines(self, position=0, callback=None):
        """
        Reads the whole file and returns the lines (separated by a line break)
        """
        self._Lock.acquire()

        def _readlines(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                readingFile.seek(position)
                data = readingFile.readlines()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _readlines(position)
        else:
            Thread(target=_readlines, args=[position, callback], daemon=True).start()

    def writelines(self, data, position=0, callback=None):
        """
        Writes (or overwrites) the given list of lines to the file
        """
        self._Lock.acquire()

        def _writelines(data, position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "w", encoding=self.encoding) as writingFile:
                writingFile.seek(position)
                writingFile.writelines((data.split("\n") if isinstance(data, str) else list(data)))
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _writelines(data, position)
        else:
            Thread(target=_writelines, args=[data, position, callback], daemon=True).start()

    def appendlines(self, data, callback=None):
        """
        Appends the given list of lines to the file
        """
        self._Lock.acquire()

        def _appendlines(data, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "a", encoding=self.encoding) as writingFile:
                writingFile.writelines((data.split("\n") if isinstance(data, str) else list(data)))
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _appendlines(data)
        else:
            Thread(target=_appendlines, args=[data, callback], daemon=True).start()

    def detach(self, mode="r", callback=None):
        """
        Returns the opened IO (TextIOWrapper)

        Warning: Make sure to close the file correctly after using the file
        """
        self._Lock.acquire()

        def _detach(mode="r", callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            fileIO = open(self.filepath, mode, encoding=self.encoding)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return fileIO
            else:
                callback(fileIO)

        if self.blocking:
            return _detach(mode)
        else:
            Thread(target=_detach, args=[mode, callback], daemon=True).start()


class BinaryFile():
    """
    A Binary File object
    """

    def __init__(self, filepath, blocking=True) -> None:
        self.filepath = str(filepath)
        self.blocking = (True if str(blocking).lower().replace(" ", "") in ["true", "yes", "1"] else False)
        self._blocking = self.blocking
        self._currentOperation = 1
        self._queueLength = 0
        self._Lock = Lock()

    def __repr__(self) -> str:
        """
        Representing the object -> str FileType: filepath
        """
        return "BinaryFile: " + self.filepath

    def __str__(self) -> str:
        """
        String representation of the object -> str filepath
        """
        return self.filepath

    def __sub__(self, other):
        """
        Substract two safeIO objects

        Returns the Cosine Similarity of the two objects (float [0;1]) if they are both instances of safeIO.TextFile or safeIO.JSONFile\n
        Returns the difference in size between the two files if one of them is a BinaryFile instance\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            return getsize(self.filepath) - getsize(other.filepath)
        else:
            return None

    def __eq__(self, other):
        """
        Checks for an equality between two safeIO objects (==)

        Returns True if the contents of the two files are the same\n
        Returns False else\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            if self.read() == other.read():
                result = True
            else:
                result = False
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        else:
            return None

    def __ne__(self, other):
        """
        Checks for an inequality between two safeIO objects (!=)

        Returns False if the contents of the two files are the same\n
        Returns True else\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            if self.read() == other.read():
                result = False
            else:
                result = True
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        else:
            return None

    def __iter__(self):
        """
        Returns self.readlines() iterator
        """
        return self.readlines().__iter__()

    def __enter__(self):
        """
        'with' statement handling
        """
        self._blocking = self.blocking
        self.blocking = True
        return self

    def __exit__(self, type, value, traceback):
        """
        Exit of 'with' statement (deleting the file)
        """
        self.blocking = self._blocking

    def isfile(self, callback=None):
        """
        Wether the file exists on the disk or not
        """
        self._Lock.acquire()

        def _isfile(callback=None):
            """
            Internal name() function
            """
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            data = isfile(self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _isfile()
        else:
            Thread(target=_isfile, args=[callback], daemon=True).start()

    def delete(self, callback=None):
        """
        Deletes the file
        """
        self._Lock.acquire()

        def _delete(callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            remove(self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _delete()
        else:
            Thread(target=_delete, args=[callback], daemon=True).start()

    def rename(self, newName, overwrite=False, callback=None):
        """
        Renames the file and returns its new path
        """
        self._Lock.acquire()

        def _rename(newName, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            oldFilepath = self.filepath
            if "/" in self.filepath:
                self.filepath = self.filepath[:self.filepath.rfind("/")] + "/" + newName
            else:
                self.filepath = newName
            while operationID != self._queueLength:
                sleep(0.001)
            if not overwrite:
                if exists(self.filepath):
                    newFilepath = self.filepath
                    self.filepath = oldFilepath
                    raise OverwriteError(newFilepath + " already exists and overwrite=False")
            rename(oldFilepath, self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return self.filepath
            else:
                callback(self.filepath)

        if self.blocking:
            return _rename(newName)
        else:
            Thread(target=_rename, args=[newName, callback], daemon=True).start()

    def move(self, newPath, overwrite=False, callback=None):
        """
        Moves the file and returns its new path
        """
        self._Lock.acquire()

        def _move(newPath, overwrite=False, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            oldFilepath = self.filepath
            self.filepath = newPath
            while operationID != self._queueLength:
                sleep(0.001)
            if not overwrite:
                if exists(self.filepath):
                    newFilepath = self.filepath
                    self.filepath = oldFilepath
                    raise OverwriteError(newFilepath + " already exists and overwrite=False")
            replace(oldFilepath, self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return self.filepath
            else:
                callback(self.filepath)

        if self.blocking:
            return _move(newPath, overwrite)
        else:
            Thread(target=_move, args=[newPath, overwrite, callback], daemon=True).start()

    def name(self, callback=None):
        """
        Returns the file name
        """
        self._Lock.acquire()

        def _name(callback=None):
            """
            Internal name() function
            """
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "rb", encoding=self.encoding) as readingFile:
                data = readingFile.name
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _name()
        else:
            Thread(target=_name, args=[callback], daemon=True).start()

    def fileno(self, callback=None):
        """
        Returns the file descriptor (int) used by Python to request I/O operations from the operating system.
        """
        self._Lock.acquire()

        def _fileno(callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "rb") as readingFile:
                data = readingFile.fileno()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _fileno()
        else:
            Thread(target=_fileno, args=[callback], daemon=True).start()

    def read(self, position=0, callback=None):
        """
        Reads the entire file and returns its content
        """
        self._Lock.acquire()

        def _read(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            if not isfile(self.filepath):
                open(self.filepath, "wb").close()
            with open(self.filepath, "rb") as readingFile:
                readingFile.seek(int(position))
                data = readingFile.read()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _read(position)
        else:
            Thread(target=_read, args=[position, callback], daemon=True).start()

    def write(self, data, position=0, callback=None):
        """
        Writes (or overwrites) to the file and returns the number of bytes written
        """
        self._Lock.acquire()

        def _write(data, position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "wb") as writingFile:
                writingFile.seek(int(position))
                data = writingFile.write(data)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _write(data, position)
        else:
            Thread(target=_write, args=[data, position, callback], daemon=True).start()

    def append(self, data, callback=None):
        """
        Appends to the file and returns the number of bytes written
        """
        self._Lock.acquire()

        def _append(data, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "ab") as writingFile:
                data = writingFile.write(data)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _append(data)
        else:
            Thread(target=_append, args=[data, callback], daemon=True).start()

    def readline(self, position=0, callback=None):
        """
        Returns the line of the current position (from the position to the linebreak)
        """
        self._Lock.acquire()

        def _readline(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "rb") as readingFile:
                readingFile.seek(int(position))
                data = readingFile.readline()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _readline(position)
        else:
            Thread(target=_readline, args=[position, callback], daemon=True).start()

    def readlines(self, position=0, callback=None):
        """
        Reads the whole file and returns the lines (separated by a line break)
        """
        self._Lock.acquire()

        def _readlines(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "rb") as readingFile:
                readingFile.seek(position)
                data = readingFile.readlines()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _readlines(position)
        else:
            Thread(target=_readlines, args=[position, callback], daemon=True).start()

    def writelines(self, data, position=0, callback=None):
        """
        Writes (or overwrites) the given list of lines to the file
        """
        self._Lock.acquire()

        def _writelines(data, position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "wb") as writingFile:
                writingFile.seek(position)
                writingFile.writelines(data)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _writelines(data, position)
        else:
            Thread(target=_writelines, args=[data, position, callback], daemon=True).start()

    def appendlines(self, data, callback=None):
        """
        Appends the given list of lines to the file
        """
        self._Lock.acquire()

        def _appendlines(data, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "ab") as writingFile:
                writingFile.writelines(data)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _appendlines(data)
        else:
            Thread(target=_appendlines, args=[data, callback], daemon=True).start()

    def detach(self, mode="rb", callback=None):
        """
        Returns the opened IO (TextIOWrapper)

        Tips: Make sure to include the "b" access mode in the mode\n
        Warning: Make sure to close the file correctly after using the file
        """
        self._Lock.acquire()

        def _detach(mode="rb", callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            fileIO = open(self.filepath, mode)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return fileIO
            else:
                callback(fileIO)

        if self.blocking:
            return _detach(mode)
        else:
            Thread(target=_detach, args=[mode, callback], daemon=True).start()


class JSONFile():
    """
    A JSON File object
    """

    def __init__(self, filepath, ensure_ascii=False, minify=False, indent=4, separators=(', ', ': '), encoding="utf-8",
                 blocking=True) -> None:
        self.filepath = str(filepath)
        self.encoding = str(encoding)
        self.blocking = (True if str(blocking).lower().replace(" ", "") in ["true", "yes", "1"] else False)
        self._blocking = self.blocking
        self.ensure_ascii = (True if str(ensure_ascii).lower().replace(" ", "") in ["true", "yes", "1"] else False)
        if (True if str(minify).lower().replace(" ", "") in ["true", "yes", "1"] else False):
            self.indent = None
            self.separators = (',', ':')
        else:
            self.indent = (int(indent) if indent is not None else None)
            self.separators = separators
        self._currentOperation = 1
        self._queueLength = 0
        self._Lock = Lock()

    def __repr__(self) -> str:
        """
        Representing the object -> str FileType: filepath
        """
        return "JSONFile: " + self.filepath

    def __str__(self) -> str:
        """
        String representation of the object -> str filepath
        """
        return self.filepath

    def __sub__(self, other):
        """
        Substract two safeIO objects

        Returns the Cosine Similarity of the two objects (float [0;1]) if they are both instances of safeIO.TextFile or safeIO.JSONFile\n
        Returns the difference in size between the two files if one of them is a BinaryFile instance\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            result = stringSimilarity(self.read(), other.read())
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        elif isinstance(other, BinaryFile):
            return getsize(self.filepath) - getsize(other.filepath)
        else:
            return None

    def __eq__(self, other):
        """
        Checks for an equality between two safeIO objects (==)

        Returns True if the contents of the two files are the same\n
        Returns False else\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            if self.read() == other.read():
                result = True
            else:
                result = False
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        else:
            return None

    def __ne__(self, other):
        """
        Checks for an inequality between two safeIO objects (!=)

        Returns False if the contents of the two files are the same\n
        Returns True else\n
        Returns None if the other object is not a safeIO object
        """
        if isinstance(other, (BinaryFile, TextFile, JSONFile)):
            currentFileBlocking = self.blocking
            otherFileBlocking = other.blocking
            self.blocking = other.blocking = True
            if self.read() == other.read():
                result = False
            else:
                result = True
            self.blocking = currentFileBlocking
            other.blocking = otherFileBlocking
            return result
        else:
            return None

    def __iter__(self):
        """
        Returns self.readlines() iterator
        """
        return self.readlines().__iter__()

    def __enter__(self):
        """
        'with' statement handling
        """
        self._blocking = self.blocking
        self.blocking = True
        return self

    def __exit__(self, type, value, traceback):
        """
        Exit of 'with' statement (deleting the file)
        """
        self.blocking = self._blocking

    def isfile(self, callback=None):
        """
        Wether the file exists on the disk or not
        """
        self._Lock.acquire()

        def _isfile(callback=None):
            """
            Internal name() function
            """
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            data = isfile(self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _isfile()
        else:
            Thread(target=_isfile, args=[callback], daemon=True).start()

    def delete(self, callback=None):
        """
        Deletes the file
        """
        self._Lock.acquire()

        def _delete(callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            remove(self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return
            else:
                callback()

        if self.blocking:
            return _delete()
        else:
            Thread(target=_delete, args=[callback], daemon=True).start()

    def rename(self, newName, overwrite=False, callback=None):
        """
        Renames the file and returns its new path
        """
        self._Lock.acquire()

        def _rename(newName, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            oldFilepath = self.filepath
            if "/" in self.filepath:
                self.filepath = self.filepath[:self.filepath.rfind("/")] + "/" + newName
            else:
                self.filepath = newName
            while operationID != self._queueLength:
                sleep(0.001)
            if not overwrite:
                if exists(self.filepath):
                    newFilepath = self.filepath
                    self.filepath = oldFilepath
                    raise OverwriteError(newFilepath + " already exists and overwrite=False")
            rename(oldFilepath, self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return self.filepath
            else:
                callback(self.filepath)

        if self.blocking:
            return _rename(newName)
        else:
            Thread(target=_rename, args=[newName, callback], daemon=True).start()

    def move(self, newPath, overwrite=False, callback=None):
        """
        Moves the file and returns its new path
        """
        self._Lock.acquire()

        def _move(newPath, overwrite=False, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            oldFilepath = self.filepath
            self.filepath = newPath
            while operationID != self._queueLength:
                sleep(0.001)
            if not overwrite:
                if exists(self.filepath):
                    newFilepath = self.filepath
                    self.filepath = oldFilepath
                    raise OverwriteError(newFilepath + " already exists and overwrite=False")
            replace(oldFilepath, self.filepath)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return self.filepath
            else:
                callback(self.filepath)

        if self.blocking:
            return _move(newPath, overwrite)
        else:
            Thread(target=_move, args=[newPath, overwrite, callback], daemon=True).start()

    def name(self, callback=None):
        """
        Returns the file name
        """
        self._Lock.acquire()

        def _name(callback=None):
            """
            Internal name() function
            """
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                data = readingFile.name
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _name()
        else:
            Thread(target=_name, args=[callback], daemon=True).start()

    def fileno(self, callback=None):
        """
        Returns the file descriptor (int) used by Python to request I/O operations from the operating system.
        """
        self._Lock.acquire()

        def _fileno(callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                data = readingFile.fileno()
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _fileno()
        else:
            Thread(target=_fileno, args=[callback], daemon=True).start()

    def read(self, position=0, callback=None):
        """
        Reads the entire file and returns its content
        """
        self._Lock.acquire()

        def _read(position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            if not isfile(self.filepath):
                open(self.filepath, "w").close()
            with open(self.filepath, "r", encoding=self.encoding) as readingFile:
                readingFile.seek(int(position))
                data = readingFile.read()
                if data.replace(" ", "") != "":
                    data = loads(data)
                else:
                    data = {}
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _read(position)
        else:
            Thread(target=_read, args=[position, callback], daemon=True).start()

    def write(self, data, position=0, callback=None):
        """
        Writes (or overwrites) to the file and returns the number of characters written
        """
        self._Lock.acquire()

        def _write(data, position=0, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "w", encoding=self.encoding) as writingFile:
                writingFile.seek(int(position))
                data = writingFile.write(
                    dumps(data, ensure_ascii=self.ensure_ascii, indent=self.indent, separators=self.separators))
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _write(data, position)
        else:
            Thread(target=_write, args=[data, position, callback], daemon=True).start()

    def append(self, data, callback=None):
        """
        Appends to the file and returns the number of characters written
        """
        self._Lock.acquire()

        def _append(data, callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            with open(self.filepath, "a", encoding=self.encoding) as writingFile:
                data = writingFile.write(
                    dumps(data, ensure_ascii=self.ensure_ascii, indent=self.indent, separators=self.separators))
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return data
            else:
                callback(data)

        if self.blocking:
            return _append(data)
        else:
            Thread(target=_append, args=[data, callback], daemon=True).start()

    def detach(self, mode="r", callback=None):
        """
        Returns the opened IO (TextIOWrapper)

        Warning: Make sure to close the file correctly after using the file
        """
        self._Lock.acquire()

        def _detach(mode="r", callback=None):
            operationID = self._queueLength = self._queueLength + 1
            while operationID != self._queueLength:
                sleep(0.001)
            fileIO = open(self.filepath, mode, encoding=self.encoding)
            self._currentOperation += 1
            self._Lock.release()
            if callback is None:
                return fileIO
            else:
                callback(fileIO)

        if self.blocking:
            return _detach(mode)
        else:
            Thread(target=_detach, args=[mode, callback], daemon=True).start()
