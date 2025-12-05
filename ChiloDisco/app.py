import os
import io
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Union

from flask import Flask, jsonify, render_template, send_from_directory, request, send_file, abort

# Try to import yaml, but provide a fallback parser if not available
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
CODE_DIR = os.path.join(BASE_DIR, 'code')
CHILO_MUTATE_PATH = os.path.join(CODE_DIR, 'ChiloMutate.py')
RELATIVE_BASE = os.path.dirname(CHILO_MUTATE_PATH) if os.path.exists(CHILO_MUTATE_PATH) else CODE_DIR
CONFIG_PATH = os.path.join(CODE_DIR, 'config.yaml')
# 若存在前端工程构建产物，则优先从该目录提供
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')

app = Flask(__name__, static_folder='static', template_folder='templates')


# 全局禁用静态与 API 缓存（对 JSON API 尤其重要）
@app.after_request
def add_no_cache_headers(response):
    if request_path_needs_no_cache():
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


def request_path_needs_no_cache() -> bool:
    try:
        from flask import request  # lazy import to avoid top-level circularity in some tools
        p = request.path or ''
        # 对 API 与首页模板禁用缓存
        return p.startswith('/api/') or p in ('/', '/health')
    except Exception:
        return False


def _manual_parse_log_paths(cfg_path: str) -> Dict[str, str]:
    """Very small, robust parser that only extracts LOG.*_PATH values.
    Supports lines like: KEY : "./output/log/file.log" or KEY: './x.log'
    """
    log_paths: Dict[str, str] = {}
    if not os.path.exists(cfg_path):
        return log_paths
    with open(cfg_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_log = False
    for raw in lines:
        line = raw.rstrip('\n')
        if not in_log:
            # Identify the LOG section start (start-of-line 'LOG')
            if line.strip().startswith('LOG'):
                in_log = True
            continue
        # Stop if we hit an empty line or next top-level section (no indent)
        if line.strip() == '' or (not line.startswith(' ') and not line.startswith('\t')):
            if log_paths:
                break
            else:
                continue
        # Expect indented KEY : VALUE
        parts = line.strip().split(':', 1)
        if len(parts) != 2:
            continue
        key, val = parts[0].strip(), parts[1].strip()
        # Remove optional comment and quotes
        if '#' in val:
            val = val.split('#', 1)[0].strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        # Remove leading colon variations like 'KEY : value'
        if key.endswith(' '):
            key = key.strip()
        if key.endswith(':'):
            key = key[:-1].strip()
        if val.startswith(':'):
            val = val[1:].strip()
        if key and val:
            log_paths[key] = val
    return log_paths


def load_log_paths() -> Dict[str, str]:
    """Load log file paths from config.yaml (LOG section). Returns absolute paths."""
    rels: Dict[str, str] = {}
    if yaml is not None:
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            logs = ((cfg or {}).get('LOG') or {})
            if isinstance(logs, dict):
                rels = {k: str(v) for k, v in logs.items()}
        except Exception:
            rels = _manual_parse_log_paths(CONFIG_PATH)
    else:
        rels = _manual_parse_log_paths(CONFIG_PATH)

    # Normalize to absolute paths relative to repo root
    abs_paths: Dict[str, str] = {}
    for k, p in rels.items():
        if not p:
            continue
        p = p.strip()
        # Support paths like ./output/log/x.log or absolute
        if not os.path.isabs(p):
            # 以 code/ChiloMutate.py 所在目录为相对路径基准（若不存在则使用 code 目录）
            p = os.path.normpath(os.path.join(RELATIVE_BASE, p))
        abs_paths[k] = p
    return abs_paths


def load_csv_paths() -> Dict[str, str]:
    """Load CSV file paths from config.yaml (CSV section). Returns absolute paths."""
    rels: Dict[str, str] = {}
    try:
        if yaml is not None:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            csvs = ((cfg or {}).get('CSV') or {})
            if isinstance(csvs, dict):
                rels = {k: str(v) for k, v in csvs.items()}
        else:
            # 简易解析：只针对 CSV 段的键值
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                in_csv = False
                for raw in f:
                    line = raw.rstrip('\n')
                    if not in_csv:
                        if line.strip().startswith('CSV'):
                            in_csv = True
                        continue
                    if line.strip() == '' or (not line.startswith(' ') and not line.startswith('\t')):
                        if rels:
                            break
                        else:
                            continue
                    parts = line.strip().split(':', 1)
                    if len(parts) != 2:
                        continue
                    key, val = parts[0].strip(), parts[1].strip()
                    if '#' in val:
                        val = val.split('#', 1)[0].strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    rels[key] = val
    except Exception:
        rels = {}

    abs_paths: Dict[str, str] = {}
    for k, p in rels.items():
        if not p:
            continue
        p = p.strip()
        if not os.path.isabs(p):
            p = os.path.normpath(os.path.join(RELATIVE_BASE, p))
        abs_paths[k] = p
    return abs_paths


LOG_PATHS = load_log_paths()


def _tail_file(path: str, max_bytes: int = 120_000, max_lines: int = 500) -> Tuple[List[str], int]:
    """Read the tail of a potentially large file efficiently.
    Returns (lines, size). Lines are decoded as UTF-8 with replacement.
    """
    if not os.path.exists(path):
        return [], 0

    size = os.path.getsize(path)
    start = max(0, size - max_bytes)
    with open(path, 'rb') as f:
        if start > 0:
            f.seek(start)
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    lines = text.splitlines()
    # If we started mid-line, drop the first partial line
    if start > 0 and lines:
        lines = lines[1:]
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return lines, size


def _file_mtime_iso(path: str) -> str:
    if not os.path.exists(path):
        return ''
    ts = os.path.getmtime(path)
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat()


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # API requests should have been handled by specific routes above or below if defined first.
    # But Flask matches strictly. We need to ensure API routes are not caught here if they are defined later?
    # Actually, specific routes take precedence.
    # But we should check if it's an API call just in case.
    if path.startswith('api/') or path.startswith('static/'):
        return abort(404)
    
    # Serve SPA entry point
    index_html = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.exists(index_html):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    
    # Fallback for dev (if dist doesn't exist, maybe serve from src? No, that requires Vite dev server)
    # If no dist, we might be in dev mode where we want to use the old templates or just tell user to build.
    # But for now, let's assume dist exists or we fallback to a simple message.
    return "Frontend not built. Please run 'npm run build' in ChiloDisco/frontend.", 200

# Keep API routes as is.



def _load_bitmap_dir() -> str:
    """从 config.yaml 的 FILE_PATH 段读取 BITMAP 目录的绝对路径。
    如果配置的是文件路径，则自动取其目录部分。"""
    file_paths = load_file_paths()
    p = file_paths.get('BITMAP', '')
    if not p:
        return ''
    # 如果路径存在但是文件，则取其目录部分
    if os.path.exists(p) and os.path.isfile(p):
        p = os.path.dirname(p)
    # 检查是否为有效目录
    if p and os.path.exists(p) and os.path.isdir(p):
        return p
    return ''


def _read_int_csv(path: str) -> List[int]:
    """读取逗号分隔整型文本，返回 list[int]。读取失败返回空列表。"""
    try:
        if not path or not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            s = f.read().strip()
        if not s:
            return []
        line = s.splitlines()[0]
        parts = [p.strip() for p in line.split(',') if p.strip() != '']
        out = []
        for x in parts:
            try:
                out.append(int(float(x)))
            except Exception:
                out.append(0)
        return out
    except Exception:
        return []


def _best_grid(n: int) -> Tuple[int, int]:
    """为长度 n 的一维数组选择接近正方形的网格 (rows, cols)。"""
    if n <= 0:
        return (0, 0)
    import math
    r = max(1, int(math.sqrt(n)))
    best = (r, (n + r - 1) // r)
    best_score = abs(best[0] - best[1]) * 1_000_000 + (best[0] * best[1] - n)
    # 在 sqrt 附近小范围搜索更优整数解
    for rows in range(max(1, r - 512), r + 513):
        cols = (n + rows - 1) // rows
        if rows * cols < n:
            cols += 1
        score = abs(rows - cols) * 1_000_000 + (rows * cols - n)
        if score < best_score:
            best = (rows, cols)
            best_score = score
    return best


@app.route('/api/bitmap/frame')
def api_bitmap_frame():
    """返回一次性的全量位图帧，包含 sum/cumulative/bool 三通道及其文件 mtime。"""
    base = _load_bitmap_dir()
    if not base:
        # 返回200状态码，但标记为错误，避免前端页面跳转
        return jsonify({
            'ok': False,
            'error': 'bitmap 目录未配置或不存在',
            'ts': datetime.now(tz=timezone.utc).isoformat(),
            'mapSize': 0,
            'layout': {'rows': 0, 'cols': 0},
            'files': {
                'sum': {'path': '', 'mtime': '', 'exists': False},
                'cumulative': {'path': '', 'mtime': '', 'exists': False},
                'bool': {'path': '', 'mtime': '', 'exists': False},
            },
            'channels': {
                'sum': [],
                'cumulative': [],
                'bool': [],
            }
        }), 200
    sum_path = os.path.join(base, 'sum.txt')
    cum_path = os.path.join(base, 'cumulative.txt')
    bool_path = os.path.join(base, 'bool.txt')

    sum_arr = _read_int_csv(sum_path)
    cum_arr = _read_int_csv(cum_path)
    bool_arr = _read_int_csv(bool_path)

    map_size = max(len(sum_arr), len(cum_arr), len(bool_arr))
    rows, cols = _best_grid(map_size)

    payload = {
        'ok': True,
        'ts': datetime.now(tz=timezone.utc).isoformat(),
        'mapSize': map_size,
        'layout': {'rows': rows, 'cols': cols},
        'files': {
            'sum': {'path': sum_path, 'mtime': _file_mtime_iso(sum_path), 'exists': os.path.exists(sum_path)},
            'cumulative': {'path': cum_path, 'mtime': _file_mtime_iso(cum_path), 'exists': os.path.exists(cum_path)},
            'bool': {'path': bool_path, 'mtime': _file_mtime_iso(bool_path), 'exists': os.path.exists(bool_path)},
        },
        'channels': {
            'sum': sum_arr,
            'cumulative': cum_arr,
            'bool': bool_arr,
        }
    }
    resp = jsonify(payload)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/api/download/bitmap')
def download_bitmap_single():
    """下载单个 bitmap 文件（sum|cumulative|bool）。"""
    which = (request.args.get('type') or '').strip().lower()
    if which not in ('sum', 'cumulative', 'bool'):
        return abort(400, description='type 应为 sum|cumulative|bool')
    base = _load_bitmap_dir()
    if not base:
        return abort(404, description='bitmap 目录不存在')
    path = os.path.join(base, f'{which}.txt')
    if not os.path.exists(path):
        return abort(404, description=f'{which}.txt 不存在')
    return send_file(path, as_attachment=True, download_name=f'{which}.txt')


@app.route('/api/download/bitmap/all')
def download_bitmap_all():
    """打包下载三种 bitmap 文本为 zip。"""
    import zipfile
    base = _load_bitmap_dir()
    if not base:
        return abort(404, description='bitmap 目录不存在')
    files = [('sum.txt', 'sum.txt'), ('cumulative.txt', 'cumulative.txt'), ('bool.txt', 'bool.txt')]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for fname, arc in files:
            p = os.path.join(base, fname)
            if os.path.exists(p):
                try:
                    zf.write(p, arcname=arc)
                except Exception:
                    zf.writestr(arc, '')
            else:
                zf.writestr(arc, '')
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'bitmap_{ts}.zip')


# ————— 下载页面与下载 API —————
@app.route('/downloads')
def downloads_page():
    return render_template('downloads.html')


@app.route('/settings')
def settings_page():
    return render_template('settings.html')


@app.route('/api/download/plot_data')
def download_plot_data():
    path = _plotdata_path()
    if not path or not os.path.exists(path):
        return abort(404, description='plot_data 不存在')
    # 使用 send_file 以附件形式下载
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@app.route('/api/download/csv/list')
def list_csvs():
    csv_paths = load_csv_paths()
    items = []
    for k, p in csv_paths.items():
        exists = os.path.exists(p)
        items.append({
            'key': k,
            'path': p,
            'exists': exists,
            'size': os.path.getsize(p) if exists else 0,
            'mtime': _file_mtime_iso(p) if exists else ''
        })
    return jsonify({'items': items})


@app.route('/api/download/csv')
def download_csv():
    key = request.args.get('key') or ''
    csv_paths = load_csv_paths()
    if key not in csv_paths:
        return abort(404, description='未知的 CSV key')
    p = csv_paths[key]
    if not p or not os.path.exists(p):
        return abort(404, description='CSV 文件不存在')
    return send_file(p, as_attachment=True, download_name=os.path.basename(p))


@app.route('/api/download/log')
def download_log():
    key = request.args.get('key') or ''
    log_paths = LOG_PATHS
    if key not in log_paths:
        return abort(404, description='未知的 LOG key')
    p = log_paths[key]
    if not p or not os.path.exists(p):
        return abort(404, description='日志文件不存在')
    return send_file(p, as_attachment=True, download_name=os.path.basename(p))


@app.route('/api/download/csv/zip')
def download_csv_zip():
    import zipfile
    buf = io.BytesIO()
    csv_paths = load_csv_paths()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for k, p in csv_paths.items():
            if p and os.path.exists(p):
                arcname = os.path.basename(p) or (k + '.csv')
                try:
                    zf.write(p, arcname=arcname)
                except Exception:
                    # 如果写入失败，写入一个占位文本
                    zf.writestr(arcname or (k + '.csv'), '')
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'chilo_csv_{ts}.zip')


def load_file_paths() -> Dict[str, str]:
    """Load file paths from config.yaml (FILE_PATH section). Returns absolute paths."""
    rels: Dict[str, str] = {}
    try:
        if yaml is not None:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            file_paths = ((cfg or {}).get('FILE_PATH') or {})
            if isinstance(file_paths, dict):
                rels = {k: str(v) for k, v in file_paths.items()}
        else:
            # 简易解析
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                in_section = False
                for raw in f:
                    line = raw.rstrip('\n')
                    if not in_section:
                        if line.strip().startswith('FILE_PATH'):
                            in_section = True
                        continue
                    if line.strip() == '' or (not line.startswith(' ') and not line.startswith('\t')):
                        if rels:
                            break
                        else:
                            continue
                    parts = line.strip().split(':', 1)
                    if len(parts) != 2:
                        continue
                    key, val = parts[0].strip(), parts[1].strip()
                    if '#' in val:
                        val = val.split('#', 1)[0].strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    rels[key] = val
    except Exception:
        rels = {}

    abs_paths: Dict[str, str] = {}
    for k, p in rels.items():
        if not p:
            continue
        p = p.strip()
        if not os.path.isabs(p):
            p = os.path.normpath(os.path.join(RELATIVE_BASE, p))
        abs_paths[k] = p
    return abs_paths


@app.route('/api/download/folder/parsed_sql')
def download_parsed_sql():
    import zipfile
    file_paths = load_file_paths()
    folder_path = file_paths.get('PARSED_SQL_PATH', '')
    if not folder_path or not os.path.exists(folder_path):
        return abort(404, description='ParsedSQL 文件夹不存在')
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                try:
                    zf.write(file_path, arcname=arcname)
                except Exception:
                    pass
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'chilo_parsed_sql_{ts}.zip')


@app.route('/api/download/folder/generated_mutator')
def download_generated_mutator():
    import zipfile
    file_paths = load_file_paths()
    folder_path = file_paths.get('GENERATED_MUTATOR_PATH', '')
    if not folder_path or not os.path.exists(folder_path):
        return abort(404, description='GeneratedMutator 文件夹不存在')
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                try:
                    zf.write(file_path, arcname=arcname)
                except Exception:
                    pass
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'chilo_generated_mutator_{ts}.zip')


@app.route('/api/download/folder/structural_sql')
def download_structural_sql():
    import zipfile
    file_paths = load_file_paths()
    folder_path = file_paths.get('STRUCTURAL_MUTATE_PATH', '')
    if not folder_path or not os.path.exists(folder_path):
        return abort(404, description='StructuralMutateSQL 文件夹不存在')
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                try:
                    zf.write(file_path, arcname=arcname)
                except Exception:
                    pass
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'chilo_structural_sql_{ts}.zip')


@app.route('/api/download/folder/queue')
def download_queue():
    import zipfile
    out_dir = _fuzz_output_dir()
    if not out_dir:
        return abort(404, description='AFL 输出目录未配置')
    
    # 优先 default/queue，回退 defaut/queue
    queue_path = os.path.join(out_dir, 'default', 'queue')
    if not os.path.exists(queue_path):
        queue_path = os.path.join(out_dir, 'defaut', 'queue')
    
    if not os.path.exists(queue_path):
        return abort(404, description='queue 文件夹不存在')
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(queue_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, queue_path)
                try:
                    zf.write(file_path, arcname=arcname)
                except Exception:
                    pass
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'afl_queue_{ts}.zip')


@app.route('/api/download/folder/crashes')
def download_crashes():
    import zipfile
    out_dir = _fuzz_output_dir()
    if not out_dir:
        return abort(404, description='AFL 输出目录未配置')
    
    # 优先 default/crashes，回退 defaut/crashes
    crash_path = os.path.join(out_dir, 'default', 'crashes')
    if not os.path.exists(crash_path):
        crash_path = os.path.join(out_dir, 'defaut', 'crashes')
    
    if not os.path.exists(crash_path):
        return abort(404, description='crashes 文件夹不存在')
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(crash_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, crash_path)
                try:
                    zf.write(file_path, arcname=arcname)
                except Exception:
                    pass
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'afl_crashes_{ts}.zip')


@app.route('/api/download/all')
def download_all():
    import zipfile
    buf = io.BytesIO()
    
    # 获取所有路径
    csv_paths = load_csv_paths()
    log_paths = load_log_paths()
    file_paths = load_file_paths()
    
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # CSV文件
        for k, p in csv_paths.items():
            if p and os.path.exists(p):
                arcname = os.path.join('csv', os.path.basename(p))
                try:
                    zf.write(p, arcname=arcname)
                except Exception:
                    pass
        
        # 日志文件
        for k, p in log_paths.items():
            if p and os.path.exists(p):
                arcname = os.path.join('logs', os.path.basename(p))
                try:
                    zf.write(p, arcname=arcname)
                except Exception:
                    pass
        
        # 文件夹
        for folder_key in ['PARSED_SQL_PATH', 'GENERATED_MUTATOR_PATH', 'STRUCTURAL_MUTATE_PATH']:
            folder_path = file_paths.get(folder_key, '')
            if folder_path and os.path.exists(folder_path):
                folder_name = os.path.basename(folder_path.rstrip('/\\'))
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(folder_name, os.path.relpath(file_path, folder_path))
                        try:
                            zf.write(file_path, arcname=arcname)
                        except Exception:
                            pass
        
        # plot_data
        plot_path = _plotdata_path()
        if plot_path and os.path.exists(plot_path):
            try:
                zf.write(plot_path, arcname=os.path.join('plot', os.path.basename(plot_path)))
            except Exception:
                pass
        
        # AFL queue 文件夹
        out_dir = _fuzz_output_dir()
        if out_dir:
            queue_path = os.path.join(out_dir, 'default', 'queue')
            if not os.path.exists(queue_path):
                queue_path = os.path.join(out_dir, 'defaut', 'queue')
            if os.path.exists(queue_path):
                for root, dirs, files in os.walk(queue_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('afl_queue', os.path.relpath(file_path, queue_path))
                        try:
                            zf.write(file_path, arcname=arcname)
                        except Exception:
                            pass
            
            # AFL crashes 文件夹
            crash_path = os.path.join(out_dir, 'default', 'crashes')
            if not os.path.exists(crash_path):
                crash_path = os.path.join(out_dir, 'defaut', 'crashes')
            if os.path.exists(crash_path):
                for root, dirs, files in os.walk(crash_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('afl_crashes', os.path.relpath(file_path, crash_path))
                        try:
                            zf.write(file_path, arcname=arcname)
                        except Exception:
                            pass
    
    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(buf, as_attachment=True, download_name=f'chilo_all_output_{ts}.zip')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True)
