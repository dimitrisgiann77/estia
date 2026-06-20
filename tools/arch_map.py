# -*- coding: utf-8 -*-
"""
arch_map.py -- Automatic data map & architecture check for Estia.

NOT part of the app. Never imported by app.py. Read-only tool.
Reads SQLAlchemy models directly from the source (single source of truth) and produces:

  1) DATA_MAP.md   -- every table, every field/type, every link (FK),
                      + who writes/reads the critical structural fields,
                      + embedded Mermaid ER diagram (graphic).
  2) DATA_MAP.html -- interactive graphic (boxes=tables, lines=links,
                      click->fields, search).
  3) --check       -- red flags: parallel "person table" / rogue writer
                      of a structural field outside the owner screens.

Usage:
    python tools/arch_map.py            # produce md + html into _arch_out/
    python tools/arch_map.py --check    # check only (exit 1 if a red flag is found)
    python tools/arch_map.py --out "<dir>"   # where to write the files

Re-run it BEFORE every release -- so the map is always accurate.
Output filenames are Greek; their content is too. Code/comments here are ASCII to stay edit-safe.
"""
import os, re, sys, json, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                       # the estia/ folder (where the .py live)

# -- Governance settings (agreement 21/06/2026) --------------------------------
# Structural registry fields that "belong" to specific screens (owner screens).
STRUCTURAL_FIELDS = ['department_id', 'home_hotel_id', 'work_hotel_id']
# Files ALLOWED to write these fields (owner screens / practical helpers).
ALLOWED_WRITERS = {'console.py', 'schedule.py', 'payroll.py', 'people.py'}
# Columns that look like "person name" / "AFM" -- for parallel-registry detection.
NAME_HINTS = ('full_name', 'fullname', 'name', 'onoma', 'lastname', 'firstname')
AFM_HINTS  = ('afm', 'vat', 'amka', 'tax_id', 'taxid')
# Tables that LEGITIMATELY hold name+AFM without user_id (legal entities, NOT persons).
# Documented exceptions -- if a new one appears, think whether it is really a non-person.
KNOWN_OK_ENTITIES = {'company'}

# Colour per module (for the graphic).
MODULE_COLOR = {
    'app.py':        '#185FA5', 'schedule.py':   '#0e7490', 'payroll.py':    '#b45309',
    'evaluations.py':'#7c3aed', 'faults.py':     '#dc2626', 'people.py':     '#15803d',
    'surveys.py':    '#db2777', 'console.py':    '#0891b2', 'extras.py':     '#64748b',
    'imports.py':    '#0d9488', 'backup.py':     '#475569', 'diag.py':       '#94a3b8',
    'menu.py':       '#64748b',
}


def camel_to_snake(name):
    """Flask-SQLAlchemy default tablename: CamelCase -> snake_case."""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def py_files():
    return sorted(f for f in os.listdir(REPO) if f.endswith('.py'))


# -- Model parser --------------------------------------------------------------
COL_RE = re.compile(r'^\s*([a-zA-Z_]\w*)\s*=\s*db\.Column\((.*)\)\s*(#.*)?$')
FK_RE  = re.compile(r"db\.ForeignKey\(\s*['\"]([^'\"]+)['\"]")
TYPE_RE= re.compile(r'db\.(\w+)')
TBL_RE = re.compile(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]")


def parse_models():
    """Returns {tablename: {cls, file, line, fields:[{name,type,fk,soft,comment}]}}."""
    tables = {}
    classname_to_table = {}
    raw = {}  # file -> lines
    for fn in py_files():
        path = os.path.join(REPO, fn)
        with open(path, encoding='utf-8') as fh:
            lines = fh.readlines()
        raw[fn] = lines
        i = 0
        while i < len(lines):
            m = re.match(r'^class\s+(\w+)\s*\(\s*db\.Model\s*\)\s*:', lines[i])
            if not m:
                i += 1; continue
            cls = m.group(1)
            start = i
            i += 1
            block, tbl_override = [], None
            # collect the class body (until the next top-level statement)
            while i < len(lines):
                ln = lines[i]
                if ln.strip() and not ln[0].isspace():  # dedent to top level
                    break
                tm = TBL_RE.search(ln)
                if tm:
                    tbl_override = tm.group(1)
                block.append(ln)
                i += 1
            tbl = tbl_override or camel_to_snake(cls)
            classname_to_table[cls] = tbl
            fields = []
            for ln in block:
                cm = COL_RE.match(ln)
                if not cm:
                    continue
                fname, args = cm.group(1), cm.group(2)
                comment = (cm.group(3) or '').lstrip('#').strip()
                fk = FK_RE.search(args)
                tm = TYPE_RE.search(args)
                fields.append({
                    'name': fname,
                    'type': tm.group(1) if tm else '?',
                    'fk': fk.group(1) if fk else None,   # 'user.id'
                    'soft': None,                        # filled below
                    'comment': comment,
                })
            tables[tbl] = {'cls': cls, 'file': fn, 'line': start + 1, 'fields': fields}
    # soft FK (_id fields without ForeignKey that point to a table by name)
    tnames = set(tables.keys())
    for tbl, info in tables.items():
        for f in info['fields']:
            if f['fk'] or not f['name'].endswith('_id'):
                continue
            base = f['name'][:-3]
            if base in tnames:
                f['soft'] = base
            else:
                for cand in tnames:                       # e.g. home_hotel_id -> hotel
                    if base.endswith(cand):
                        f['soft'] = cand; break
    return tables, classname_to_table, raw


# -- Structural-field usage scan (who writes / reads) --------------------------
def usage_scan():
    """For each structural field: writers (assignment) & readers per file (.py + templates)."""
    targets = []
    tdir = os.path.join(REPO, 'templates')
    for fn in py_files():
        targets.append(os.path.join(REPO, fn))
    if os.path.isdir(tdir):
        for fn in sorted(os.listdir(tdir)):
            if fn.endswith('.html'):
                targets.append(os.path.join(tdir, fn))
    usage = {f: {'write': {}, 'read': {}} for f in STRUCTURAL_FIELDS}
    for path in targets:
        rel = os.path.relpath(path, REPO).replace('\\', '/')
        try:
            with open(path, encoding='utf-8') as fh:
                text = fh.read()
        except Exception:
            continue
        for field in STRUCTURAL_FIELDS:
            # write: .field =   (but not ==, <=, >=, !=)
            w = len(re.findall(r'\.' + field + r'\s*=(?![=])', text))
            # read: every .field that is not an assignment
            allc = len(re.findall(r'\.' + field + r'\b', text))
            r = max(allc - w, 0)
            if w: usage[field]['write'][rel] = w
            if r: usage[field]['read'][rel]  = r
    return usage


# -- Red flags -----------------------------------------------------------------
def field_owner_files(tables):
    """field -> set of files that declare a model with that column.
    (If a file 'owns' the column, a write there is legitimate -- e.g. a snapshot.)"""
    owners = {f: set() for f in STRUCTURAL_FIELDS}
    for info in tables.values():
        names = {fl['name'] for fl in info['fields']}
        for field in STRUCTURAL_FIELDS:
            if field in names:
                owners[field].add(info['file'])
    return owners


def red_flags(tables):
    flags = []
    # 1) Parallel person registry: name + AFM but WITHOUT user_id
    for tbl, info in tables.items():
        if tbl == 'user' or tbl in KNOWN_OK_ENTITIES:
            continue
        fnames = {f['name'].lower() for f in info['fields']}
        has_name = any(any(h == n or n.endswith('_' + h) for h in NAME_HINTS) for n in fnames)
        has_afm  = any(any(h in n for h in AFM_HINTS) for n in fnames)
        has_uid  = any(f['name'] == 'user_id' or (f['fk'] or '').startswith('user.') for f in info['fields'])
        if has_name and has_afm and not has_uid:
            flags.append(('PARALLEL REGISTRY?', '%s (%s): has name+AFM without user_id FK -- '
                          'possible parallel person table.' % (info['cls'], info['file'])))
    # 2) Rogue writer of a structural field outside the owner screens.
    #    Exception: files that OWN the column in their own model (e.g. Evaluation.department_id snapshot).
    usage = usage_scan()
    owners = field_owner_files(tables)
    for field in STRUCTURAL_FIELDS:
        for rel, n in usage[field]['write'].items():
            base = rel.split('/')[-1]
            if base.endswith('.py') and base not in ALLOWED_WRITERS and base not in owners[field]:
                flags.append(('ROGUE WRITER', '%s writes .%s (%dx) -- outside the approved '
                              'owner screens %s.' % (rel, field, n, sorted(ALLOWED_WRITERS))))
    return flags, usage


# -- Markdown (+ Mermaid) ------------------------------------------------------
def build_md(tables, cls2tbl, usage, flags):
    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    by_file = {}
    for tbl, info in tables.items():
        by_file.setdefault(info['file'], []).append((tbl, info))
    out = []
    A = out.append
    A('# DATA MAP -- Estia (auto-generated)')
    A('')
    A('> Generated by `tools/arch_map.py` reading the models from the code. '
      '**Do not edit by hand** -- re-run the tool. Last generated: %s' % now)
    A('')
    A('Tables: **%d** | Model files: **%d**' % (len(tables), len(by_file)))
    A('')
    if flags:
        A('## RED FLAGS (%d)' % len(flags))
        A('')
        for kind, msg in flags:
            A('- **%s** -- %s' % (kind, msg))
        A('')
    else:
        A('## OK -- no red flags')
        A('')

    A('## Who writes/reads the structural registry fields')
    A('')
    A('Critical for the "owner screen" principle: these fields must be **written** only by the '
      'approved screens; everyone else **reads** them.')
    A('')
    owners = field_owner_files(tables)
    decl = {}
    for info in tables.values():
        for fl in info['fields']:
            if fl['name'] in STRUCTURAL_FIELDS:
                decl.setdefault(fl['name'], []).append(info['cls'])
    for field in STRUCTURAL_FIELDS:
        A('### `User.%s`' % field)
        A('')
        d = decl.get(field, [])
        if len(d) > 1:
            A('> NOTE: column `%s` is declared in **%d** tables: %s. '
              'The write/read counts are per field name -- a write to its own table '
              '(e.g. a snapshot) is legitimate.' % (field, len(d), ', '.join('`%s`' % x for x in d)))
            A('')
        w = usage[field]['write']; r = usage[field]['read']
        A('- **Write:** %s' % (', '.join('`%s`x%d' % (k, v) for k, v in sorted(w.items())) or '--'))
        A('- **Read:** %s' % (', '.join('`%s`x%d' % (k, v) for k, v in sorted(r.items())) or '--'))
        A('')

    A('## Link diagram (Mermaid ER)')
    A('')
    A('```mermaid')
    A('erDiagram')
    seen = set()
    for tbl, info in tables.items():
        for f in info['fields']:
            target = None
            if f['fk']:
                target = f['fk'].split('.')[0]
            elif f['soft']:
                target = f['soft']
            if target and target in tables and target != tbl:
                key = (tbl, target, f['name'])
                if key in seen:
                    continue
                seen.add(key)
                rel = '..' if f['soft'] else '--'
                A('    %s }o%so|| %s : "%s%s"' % (
                    tbl.upper(), rel, target.upper(), f['name'],
                    ' (soft)' if f['soft'] else ''))
    A('```')
    A('')
    A('_Solid line = real FK | dashed/(soft) = link by naming convention without a DB FK._')
    A('')

    A('## Tables & fields (per module)')
    A('')
    for fn in sorted(by_file.keys()):
        A('### `%s`' % fn)
        A('')
        for tbl, info in sorted(by_file[fn]):
            A('#### %s  ::  `%s`  (line %d)' % (info['cls'], tbl, info['line']))
            A('')
            A('| Field | Type | Link | Comment |')
            A('|---|---|---|---|')
            for f in info['fields']:
                link = ''
                if f['fk']:
                    link = '-> %s (FK)' % f['fk']
                elif f['soft']:
                    link = '-> %s (soft)' % f['soft']
                A('| `%s` | %s | %s | %s |' % (f['name'], f['type'], link,
                                               f['comment'].replace('|', '\\|')))
            A('')
    return '\n'.join(out)


# -- Interactive HTML (vis-network from CDN) -----------------------------------
def build_html(tables, cls2tbl, usage, flags):
    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    nodes, edges = [], []
    for tbl, info in tables.items():
        color = MODULE_COLOR.get(info['file'], '#64748b')
        nodes.append({
            'id': tbl, 'label': info['cls'], 'group': info['file'], 'color': color,
            'fields': [{'name': f['name'], 'type': f['type'],
                        'link': (f['fk'] and ('-> ' + f['fk'])) or (f['soft'] and ('-> ' + f['soft'] + ' (soft)')) or '',
                        'comment': f['comment']} for f in info['fields']],
            'file': info['file'],
        })
    seen = set()
    for tbl, info in tables.items():
        for f in info['fields']:
            target = (f['fk'].split('.')[0] if f['fk'] else f['soft'])
            if target and target in tables and target != tbl:
                key = (tbl, target, f['name'])
                if key in seen:
                    continue
                seen.add(key)
                edges.append({'from': tbl, 'to': target, 'label': f['name'],
                              'dashes': bool(f['soft'])})
    flags_html = ''.join('<li><b>%s</b> -- %s</li>' % (html.escape(k), html.escape(m)) for k, m in flags)
    data = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False)
    legend = ''.join('<span class="lg"><i style="background:%s"></i>%s</span>' % (c, html.escape(f))
                     for f, c in sorted(MODULE_COLOR.items()))
    return TEMPLATE.replace('__DATA__', data).replace('__NOW__', now)\
                   .replace('__FLAGS__', flags_html or '<li>OK -- none</li>')\
                   .replace('__NTAB__', str(len(tables))).replace('__LEGEND__', legend)


TEMPLATE = r"""<!DOCTYPE html><html lang="el"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chartis Dedomenon -- Estia</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  *{box-sizing:border-box;} body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1e293b;background:#eef2f5;}
  header{background:#193847;color:#fff;padding:12px 18px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
  header h1{font-size:16px;margin:0;} header .sub{font-size:11.5px;color:#cfe1f5;}
  #search{margin-left:auto;padding:7px 11px;border-radius:8px;border:none;font-size:13px;min-width:200px;}
  .wrap{display:flex;height:calc(100vh - 52px);}
  #net{flex:1;background:#f8fafc;}
  #side{width:340px;background:#fff;border-left:1px solid #e2e8f0;overflow:auto;padding:14px;}
  #side h2{font-size:14px;margin:0 0 2px;color:#193847;} #side .f{font-size:11px;color:#64748b;margin:0 0 10px;}
  table{width:100%;border-collapse:collapse;font-size:12px;} th{background:#193847;color:#fff;text-align:left;padding:5px 7px;font-size:11px;}
  td{padding:4px 7px;border-bottom:1px solid #eef2f5;vertical-align:top;} td.l{color:#0e7490;white-space:nowrap;}
  .empty{color:#94a3b8;font-size:12.5px;margin-top:30px;text-align:center;}
  .flags{background:#fff7ed;border:1px solid #fed7aa;border-radius:9px;padding:9px 12px;margin-bottom:12px;font-size:12px;}
  .flags ul{margin:6px 0 0;padding-left:18px;} .flags li{margin-bottom:4px;}
  .legend{padding:7px 14px;background:#fff;border-bottom:1px solid #e2e8f0;font-size:11px;display:flex;gap:12px;flex-wrap:wrap;}
  .lg{display:inline-flex;align-items:center;gap:5px;} .lg i{width:11px;height:11px;border-radius:3px;display:inline-block;}
</style></head><body>
<header>
  <div><h1>Chartis Dedomenon -- Estia</h1>
  <div class="sub">__NTAB__ tables | auto from code | __NOW__ | click a table -> fields</div></div>
  <input id="search" placeholder="Search table/field...">
</header>
<div class="legend">__LEGEND__</div>
<div class="wrap">
  <div id="net"></div>
  <div id="side">
    <div class="flags"><b>RED FLAGS</b><ul>__FLAGS__</ul></div>
    <div class="empty" id="hint">Click a table to see its fields.</div>
    <div id="detail"></div>
  </div>
</div>
<script>
var DATA = __DATA__;
var nodes = new vis.DataSet(DATA.nodes.map(function(n){
  return {id:n.id, label:n.label, color:{background:n.color,border:'#1e293b'},
          font:{color:'#fff',size:13}, shape:'box', margin:8};
}));
var edges = new vis.DataSet(DATA.edges.map(function(e,i){
  return {id:i, from:e.from, to:e.to, label:e.label, dashes:e.dashes,
          font:{size:9,color:'#64748b',strokeWidth:3,strokeColor:'#f8fafc'},
          arrows:{to:{enabled:true,scaleFactor:0.5}}, color:{color:e.dashes?'#cbd5e1':'#94a3b8'}};
}));
var byId={}; DATA.nodes.forEach(function(n){byId[n.id]=n;});
var net = new vis.Network(document.getElementById('net'), {nodes:nodes,edges:edges}, {
  physics:{stabilization:true, barnesHut:{gravitationalConstant:-9000,springLength:140}},
  interaction:{hover:true, tooltipDelay:120}
});
function show(id){
  var n=byId[id]; if(!n){return;}
  document.getElementById('hint').style.display='none';
  var rows=n.fields.map(function(f){
    return '<tr><td>'+f.name+'</td><td style="color:#64748b">'+f.type+'</td>'+
           '<td class="l">'+(f.link||'')+'</td></tr>';
  }).join('');
  document.getElementById('detail').innerHTML =
    '<h2>'+n.label+'</h2><div class="f">'+n.id+' | '+n.file+'</div>'+
    '<table><tr><th>Field</th><th>Type</th><th>Link</th></tr>'+rows+'</table>';
}
net.on('click', function(p){ if(p.nodes.length){ show(p.nodes[0]); } });
document.getElementById('search').addEventListener('input', function(e){
  var q=e.target.value.toLowerCase().trim();
  if(!q){ nodes.forEach(function(n){nodes.update({id:n.id,hidden:false});}); return; }
  DATA.nodes.forEach(function(n){
    var hit = n.id.indexOf(q)>=0 || n.label.toLowerCase().indexOf(q)>=0 ||
              n.fields.some(function(f){return f.name.toLowerCase().indexOf(q)>=0;});
    nodes.update({id:n.id, hidden:!hit});
  });
});
</script></body></html>"""


def main():
    args = sys.argv[1:]
    out_dir = os.path.join(os.getcwd(), '_arch_out')
    if '--out' in args:
        out_dir = args[args.index('--out') + 1]
    check_only = '--check' in args

    tables, cls2tbl, raw = parse_models()
    flags, usage = red_flags(tables)

    if check_only:
        print('arch_map --check: %d tables' % len(tables))
        if flags:
            print('%d red flags:' % len(flags))
            for k, m in flags:
                print('  - [%s] %s' % (k, m))
            sys.exit(1)
        print('OK -- no red flags.')
        sys.exit(0)

    os.makedirs(out_dir, exist_ok=True)
    md = build_md(tables, cls2tbl, usage, flags)
    htm = build_html(tables, cls2tbl, usage, flags)
    md_path = os.path.join(out_dir, 'ΧΑΡΤΗΣ_ΔΕΔΟΜΕΝΩΝ.md')
    html_path = os.path.join(out_dir, 'ΧΑΡΤΗΣ_ΔΕΔΟΜΕΝΩΝ.html')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(htm)
    print('Produced:')
    print('   ', md_path)
    print('   ', html_path)
    print('Tables: %d | Red flags: %d' % (len(tables), len(flags)))
    for k, m in flags:
        print('   [%s] %s' % (k, m))


if __name__ == '__main__':
    main()
