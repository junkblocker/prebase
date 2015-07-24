#!/usr/bin/env python3

"'rebaser' improves on 'git rebase -i' by adding information per commit regarding which files it touched."

from subprocess import check_call, check_output
from itertools import count, chain
from collections import defaultdict
from string import digits, ascii_letters

SYMBOLS = dict(enumerate(chain(digits, ascii_letters)))
SPACER = "_"


def parse_log(first, last):

    gitlog = check_output([
        'git', 'log', '--name-only', '--oneline', '--no-color',
        '--format=#commit %h {idx:4}:%s',
        "%s^..%s" % (first, last)],
        universal_newlines=True)

    lines = iter(gitlog.splitlines())
    line = next(lines)

    while True:
        prefix, _, commit = line.partition(" ")
        assert prefix == "#commit"

        files = set()
        for line in lines:
            if line.startswith("#commit"):
                yield (commit, sorted(files))
                break  # for
            elif line:
                files.add(line)
        else:
            yield (commit, sorted(files))
            break  # while


def compact(line, length, ellipsis="....", suffix_length=10):
    if len(line) <= length:
        return line
    return line[:length-len(ellipsis)-suffix_length] + ellipsis + line[-suffix_length:]


def symbol(idx):
    return SYMBOLS[idx % len(SYMBOLS)]


def write_todo(file, first, last, comments):
    c = count(0)
    file_indices = defaultdict(lambda: next(c))
    lines = []
    log = list(parse_log(first, last))
    width = min(120, max(len(c) for (c, _) in log) if log else 80)
    for commit, files in log:
        indices = {file_indices[f] for f in files}
        placements = "".join(symbol(i) if i in indices else SPACER for i in range(max(indices)+1)) if indices else ""
        lines.append((compact(commit, width).ljust(width), placements))
    lines.reverse()
    placements_width = max(file_indices.values()) + 2
    for i, (commit, placements) in enumerate(lines, 1):
        print("pick", commit.format(idx=i), placements.ljust(placements_width, SPACER), file=file)

    print("", file=file)
    for f, i in sorted(file_indices.items(), key=lambda p: p[1]):
        pos = symbol(i).rjust(1+i, SPACER).ljust(placements_width, SPACER)
        f = "[%s] %s" % (symbol(i), f)
        fname = compact("# %s" % f, width+2).ljust(width+2)
        print(fname, pos, file=file)

    print("", file=file)
    print(comments, file=file)


if __name__ == '__main__':
    import sys
    import os

    if len(sys.argv) <= 1:
        print("\n\t%s <branch>\n" % sys.argv[0])
        sys.exit(1)

    if not os.path.isfile(sys.argv[1]):
        base_commit = sys.argv[1]
        git_editor = check_output(["git", "var", "GIT_EDITOR"], universal_newlines=True).strip()
        os.environ['GIT_ORIG_EDITOR'] = os.path.expanduser(git_editor)
        os.environ['GIT_EDITOR'] = __file__
        os.execlpe("git", "git", "rebase", "-i", base_commit, os.environ)

    todo_file = sys.argv[1]
    os.environ['GIT_EDITOR'] = editor = os.environ['GIT_ORIG_EDITOR']

    if not todo_file.endswith("git-rebase-todo"):
        os.execlpe(editor, editor, todo_file, os.environ)

    commits = []

    with open(todo_file) as f:
        for line in f:
            if not line.strip():
                break
            commits.append(line.split()[1])
        comments = f.read()

    first, *_, last = commits
    with open(todo_file, "w") as file:
        write_todo(file, first, last, comments)

    check_call([editor, todo_file])
