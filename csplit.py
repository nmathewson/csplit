

import re, os, sys, logging

fn_1_re = re.compile(r'^([a-zA-Z0-9][a-zA-Z0-9_]*),?\(')

struct_1_re = re.compile(r'^(?:typedef )struct ([a-zA-Z0-9][a-zA-Z0-9_]*) {')

UNFUNCTIONS = set(["MOCK_IMPL", "MOCK_DECL",
                   "HT_GENERATE", "HT_GENERATE2", "HT_PROTOTYPE",
                   "DISABLE_GCC_WARNING", "ENABLE_GCC_WARNING",
                   "DECLARE_CTYPE_FN" ])

def lex_c_file(f):
    for line in f:
        if line.startswith("/**"):
            yield "Doxy", None, line
            continue
        m = fn_1_re.match(line)
        if m and m.group(1) not in UNFUNCTIONS and ";" not in line:
            yield "Func", m.group(1), line
            continue
        m = struct_1_re.match(line)
        if m:
            yield "Struct", m.group(1), line
            continue

        if line.startswith("}"):
            yield "EndOfDef", None, line
        else:
            yield "Other", None, line

def find_last_break_idx(b):
    for idx in range(len(b)-1, -1, -1):
        tp, content = b[idx]
        if tp == "Doxy" or (tp == "Other" and content.strip() == ""):
            return idx
    return None

def split_blob(b):
    idx = find_last_break_idx(b)
    if idx == None or idx == 0:
        return ([], b)
    else:
        return (b[:idx], b[idx:])

def chunk_c_file(f):
    current_blob = []
    in_def = False
    blob_name = None

    for tp, name, line in lex_c_file(f):
        current_blob.append((tp, line))
        if tp == "Other" or tp == "Doxy":
            pass
        elif tp == "Func" or tp == "Struct":
            prev, cur = split_blob(current_blob)
            yield (blob_name, prev)
            current_blob = cur
            blob_name = name
            in_def = True
        elif tp == "EndOfDef":
            if in_def:
                yield (blob_name, current_blob)
                current_blob = []
                blob_name = None
                in_def = False
    yield (blob_name, current_blob)

def join_blob(b):
    return "".join(content for (tp, content) in b)

def make_uniq_name(base, used):
    name = base
    idx = 0
    while name in used:
        idx += 1
        name = "%s_%s"%(base, idx)
    used.add(name)
    return name

def split_one_c_file(fname, outdir, used):
    logging.info("Splitting %s",fname)
    basename = os.path.split(fname)[1]
    master = []
    with open(fname, 'r') as inp:
        for blob_name, blob in chunk_c_file(inp):
            if blob_name:
                outname = make_uniq_name(blob_name, used)
                master.append(("Include", '#include "%s"\n'%(outname)))
                outname = os.path.join(outdir, outname)
                with open(outname, 'w') as out:
                    out.write(join_blob(blob))
            else:
                master.extend(blob)

    outname = make_uniq_name(basename, used)
    outname = os.path.join(outdir, outname)
    with open(outname, 'w') as out:
        out.write(join_blob(master))

def split_c_files(fnames, outdir):
    used = set()
    for fname in fnames:
        split_one_c_file(fname, outdir, used)

if __name__ == '__main__':
    if not os.path.isdir("OUT_SPLIT"):
        os.makedirs("OUT_SPLIT")
    split_c_files(sys.argv[1:], "OUT_SPLIT")
