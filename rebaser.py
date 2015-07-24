#!/usr/bin/env python3
from subprocess import check_call, check_output


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


def write_todo(file, first, last, comments):
    from itertools import count, chain
    from collections import defaultdict
    from string import digits, ascii_letters
    c = count(0)
    file_indices = defaultdict(lambda: next(c))
    SYM = dict(enumerate(chain(digits, ascii_letters)))
    lines = []
    log = list(parse_log(first, last))
    width = min(120, max(len(c) for (c, _) in log) if log else 80)
    for commit, files in log:
        indices = {file_indices[f] for f in files}
        placements = "".join(SYM[i % len(SYM)] if i in indices else "~" for i in range(max(indices)+1)) if indices else ""
        lines.append((compact(commit, width).ljust(width), placements))
    lines.reverse()

    for i, (commit, placements) in enumerate(lines, 1):
        print("pick", commit.format(idx=i), placements, file=file)

    print("", file=file)
    for f, i in sorted(file_indices.items(), key=lambda p: p[1]):
        pos = SYM[i % len(SYM)].rjust(1+i, "~")
        f = "[%s] %s" % (SYM[i], f)
        fname = compact("# %s" % f, width+2).ljust(width+2)
        print(fname, pos, file=file)

    print("", file=file)
    print(comments, file=file)


if __name__ == '__main__':
    import sys
    import os

    if not os.path.isfile(sys.argv[1]):
        base_commit = sys.argv[1]
        os.environ['GIT_ORIG_EDITOR'] = check_output(["git", "var", "GIT_EDITOR"], universal_newlines=True).strip()
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
    # subl['-n', '-w', todo_file] & FG
