# SPDX-License-Identifier: MIT
import re, logging, sys, os, stat, shutil

def ssize(v):
    suffixes = ["B", "KB", "MB", "GB", "TB"]
    for i in suffixes:
        if v < 1000 or i == suffixes[-1]:
            if isinstance(v, int):
                return f"{v} {i}"
            else:
                return f"{v:.2f} {i}"
        v /= 1000

def psize(v, align=None):
    v = v.upper().replace(" ", "")
    base = 1000
    if v[-2] == "I":
        base = 1024
        v = v[:-2] + v[-1]
    suffixes = {"TB": 4, "GB": 3, "MB": 2, "KB": 1, "B": 0, "": 0}
    for suffix, power in suffixes.items():
        if v.endswith(suffix):
            val = int(float(v[:-len(suffix)]) * (base ** power))
            break
    else:
        return None
    if align is not None:
        if isinstance(align, str):
            align = psize(align)
            assert align is not None
        val = align_up(val, align)
    return val

def split_ver(s):
    parts = re.split(r"[-. ]", s)
    parts2 = []
    for i in parts:
        try:
            parts2.append(int(i))
        except ValueError:
            parts2.append(i)
    if len(parts2) > 3 and parts2[-2] == "beta":
        parts2[-3] -= 1
        parts2[-2] = 99
    return tuple(parts2)

def align_up(v, a=16384):
    return (v + a - 1) & ~(a - 1)

align = align_up

def align_down(v, a=16384):
    return v & ~(a - 1)

BLACK     = 30
RED       = 31
GREEN     = 32
YELLOW    = 33
BLUE      = 34
MAGENTA   = 35
CYAN      = 36
WHITE     = 37

BRIGHT    = 1
DIM       = 2
NORMAL    = 22
RESET_ALL = 0

def col(*color):
    color = ";".join(map(str, color))
    return f"\033[{color}m"

def p_style(*args, color=[], **kwargs):
    if isinstance(color, int):
        color = [color]
    text = " ".join(map(str, args))
    print(col(*color) + text + col(), **kwargs)
    if "\033" in text:
        text += col()
    logging.info(f"MSG: {text}")

def p_plain(*args):
    p_style(*args)

def p_info(*args):
    p_style(*args, color=(BRIGHT, BLUE))

def p_progress(*args):
    p_style(*args, color=(BRIGHT, MAGENTA))

def p_message(*args):
    p_style(*args, color=BRIGHT)

def p_error(*args):
    p_style(*args, color=(BRIGHT, RED))

def p_warning(*args):
    p_style(*args, color=(BRIGHT, YELLOW))

def p_question(*args):
    p_style(*args, color=(BRIGHT, CYAN))

def p_success(*args):
    p_style(*args, color=(BRIGHT, GREEN))

def p_prompt(*args):
    p_style(*args, color=(BRIGHT, CYAN))

def p_choice(*args):
    p_style(*args)

def input_prompt(*args):
    while True:
        p_style(f"{col(BRIGHT, WHITE)}»{col(BRIGHT, CYAN)}", *args, end="")
        val = input()
        if any (ord(c) < 0x20 for c in val):
            p_error("Invalid input")
            continue
        break
    logging.info(f"INPUT: {val!r}")
    return val

class PackageInstaller:
    def __init__(self):
        self.verbose = "-v" in sys.argv
        self.printed_progress = False

    def flush_progress(self):
        if self.ucache and self.ucache.flush_progress():
            self.printed_progress = False
            return
        if self.printed_progress:
            sys.stdout.write("\n")
            self.printed_progress = False

    def extract(self, src, dest):
        logging.info(f"  {src} -> {dest}/")
        self.pkg.extract(src, dest)

    def fdcopy(self, sfd, dfd, size=None):
        BLOCK = 128 * 1024 * 1024
        copied = 0
        while True:
            if size is not None:
                prog = copied / size * 100
                sys.stdout.write(f"\033[3G{prog:6.2f}% ")
                sys.stdout.flush()
                self.printed_progress = True
            d = sfd.read(BLOCK)
            if not d:
                break
            dfd.write(d)
            copied += len(d)

        if size is not None:
            sys.stdout.write("\033[3G100.00% ")
            sys.stdout.flush()

    def extract_file(self, src, dest, optional=True):
        try:
            info = self.pkg.getinfo(src)
            with self.pkg.open(src) as sfd, \
                open(dest, "wb") as dfd:
                logging.info(f"  {src} -> {dest}")
                self.fdcopy(sfd, dfd, info.file_size)
        except KeyError:
            if not optional:
                raise
        if self.verbose:
            self.flush_progress()

    def extract_tree(self, src, dest):
        if src[-1] != "/":
            src += "/"
        logging.info(f"  {src}* -> {dest}")

        infolist = self.pkg.infolist()
        if self.verbose:
            self.flush_progress()

        for info in infolist:
            name = info.filename
            if not name.startswith(src):
                continue
            subpath = name[len(src):]
            assert subpath[0:1] != "/"

            destpath = os.path.join(dest, subpath)

            if info.is_dir():
                os.makedirs(destpath, exist_ok=True)
            elif stat.S_ISLNK(info.external_attr >> 16):
                link = self.pkg.open(info.filename).read()
                if os.path.lexists(destpath):
                    os.unlink(destpath)
                os.symlink(link, destpath)
            else:
                self.extract_file(name, destpath)

            if self.verbose:
                self.flush_progress()
