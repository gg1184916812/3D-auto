# -*- coding: utf-8 -*-
import os, sys, json, time, shutil, subprocess, urllib.request, urllib.parse, msvcrt
from pathlib import Path

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
OUTPUT_FILE = Path("./training_dataset.jsonl")
URL_CACHE_FILE = Path("./url_cache.json")
SHARED_DOWNLOADS_DIR = Path("./shared_downloads")
SHARED_DOWNLOAD_LOG = Path("./shared_downloads.txt")

GROQ_KEY = os.environ.get("GROQ_KEY", "")
MISTRAL_KEY = os.environ.get("MISTRAL_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "")
OLLAMA_PASSWORD = os.environ.get("OLLAMA_PASSWORD", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {"User-Agent": "Mozilla/5.0"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = "token {0}".format(GITHUB_TOKEN)

SHARED_DOWNLOADS_DIR.mkdir(exist_ok=True)

REPOS_WITH_GEONODES = [
    "BradyAJohnston/MolecularNodes",
    "node-dojo/dojo-recursive-bins",
    "al1brn/geonodes",
    "vevenom/pytorchgeonodes",
    "rbarbosa51/GeometryNodesByTutorials",
    "cgvirus/blender-geometry-nodes-collection",
    "Rideu/generative-blender",
    "IRCSS/Blender-Geometry-Node-French-Houses",
    "IRCSS/Trees-With-Geometry-Nodes-Blender",
    "RanmanEmpire/RM_SubdivisionSurface",
    "RanmanEmpire/RM_CurveMorph",
    "fletchgraham/fletchnodes",
    "Tams3d/T3D-GN-Presets",
    "MACHIN3tools/MACHIN3",
    "simo-esi/Blender-Geometry-Nodes-Collection",
    "sobotka/Blender-Game-Engine",
    "geo-data/blender-geodata",
    "artfunkel/blender-geodesic",
    "CFDXF/BlenderCityCons",
    "BD3D/Blender-ADDON",
]

KNOWN_WORKING_URLS = [
    "https://raw.githubusercontent.com/BradyAJohnston/MolecularNodes/HEAD/molecularnodes/assets/node_data_file.blend",
    "https://raw.githubusercontent.com/BradyAJohnston/MolecularNodes/HEAD/molecularnodes/assets/template/startup.blend",
    "https://raw.githubusercontent.com/BradyAJohnston/MolecularNodes/HEAD/tests/data/blendfiles/suzanne.blend",
    "https://raw.githubusercontent.com/node-dojo/dojo-recursive-bins/HEAD/Dojo%20Bin%20Generator_recursive%202%20step_v0.1.1.blend",
    "https://raw.githubusercontent.com/node-dojo/dojo-recursive-bins/HEAD/Dojo%20Bin%20Generator_recursive%20red%20bins_v.0.1.1.blend",
    "https://raw.githubusercontent.com/al1brn/geonodes/HEAD/generation/gen%20V5.blend",
    "https://raw.githubusercontent.com/al1brn/geonodes/HEAD/generation/gen%20auto.blend",
    "https://raw.githubusercontent.com/al1brn/geonodes/HEAD/generation/gendoc.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/bed.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/cabinet.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/cabinet_div_boards_vis.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/chair.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/chair2.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/chair_safe.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/sofa.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/table.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/cube.blend",
    "https://raw.githubusercontent.com/vevenom/pytorchgeonodes/HEAD/ShapeProgramsDataset/test.blend",
]

CHAPTER_URLS = []
for chap in range(1, 41):
    for suffix in ["Final", "Start"]:
        CHAPTER_URLS.append(f"https://raw.githubusercontent.com/rbarbosa51/GeometryNodesByTutorials/HEAD/Chapter{chap:02d}/Chapter{chap:02d}{suffix}.blend")

BLENDER_DEMO_URLS = [
    "https://download.blender.org/demo/geometry-nodes/4D_Gaussian_Splatting-Nunchucks_and_cat.blend",
    "https://download.blender.org/demo/geometry-nodes/SDF_mixer_kitbukoros.blend",
    "https://download.blender.org/demo/geometry-nodes/abstract_monkey_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/accumulate_field.blend",
    "https://download.blender.org/demo/geometry-nodes/ball-in-grass_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/chocolate.blend",
    "https://download.blender.org/demo/geometry-nodes/cubic-whirlpool_geometry-nodes-demo.blend",
    "https://download.blender.org/demo/geometry-nodes/field_at_index.blend",
    "https://download.blender.org/demo/geometry-nodes/flower_scattering.blend",
    "https://download.blender.org/demo/geometry-nodes/food_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/instance_attribtues.blend",
    "https://download.blender.org/demo/geometry-nodes/procedural_vine.blend",
    "https://download.blender.org/demo/geometry-nodes/scatter_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/hair_strands.blend",
    "https://download.blender.org/demo/geometry-nodes/ocean_waves.blend",
    "https://download.blender.org/demo/geometry-nodes/city_generator.blend",
    "https://download.blender.org/demo/geometry-nodes/terrain_gen.blend",
    "https://download.blender.org/demo/geometry-nodes/procedural_vine.blend",
    "https://download.blender.org/demo/geometry-nodes/scatter_demo.blend",
]

def fetch_blend_urls_from_repo(repo):
    urls = []
    try:
        url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get('tree', []):
                path = item.get('path', '')
                if path.endswith('.blend'):
                    safe_path = urllib.parse.quote(path, safe='/')
                    urls.append(f"https://raw.githubusercontent.com/{repo}/HEAD/{safe_path}")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  API 限流: {0}".format(repo))
        else:
            print("  HTTP 錯誤 {1}: {0}".format(repo, e.code))
    except Exception as e:
        print("  獲取失敗 {0}: {1}".format(repo, e))
    return urls

def load_cached_urls():
    if URL_CACHE_FILE.exists():
        try:
            with open(URL_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def save_cached_urls(urls):
    try:
        with open(URL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(urls, f)
    except:
        pass

def fetch_all_urls():
    cached = load_cached_urls()
    if cached:
        print("使用快取 URL: {0} 個".format(len(cached)))
        return cached
    
    if GITHUB_TOKEN:
        print("GitHub Token: 已設定 (可用於提高 API 限流)")
    else:
        print("GitHub Token: 未設定 (API 限流可能較低)")
    
    all_urls = list(KNOWN_WORKING_URLS)
    all_urls.extend(CHAPTER_URLS)
    all_urls.extend(BLENDER_DEMO_URLS)
    
    print("從 GitHub 倉庫搜索 blend 檔案...")
    for repo in REPOS_WITH_GEONODES:
        urls = fetch_blend_urls_from_repo(repo)
        if urls:
            print("  {0}: 找到 {1} 個 blend 檔".format(repo, len(urls)))
            all_urls.extend(urls)
        else:
            print("  {0}: 獲取失敗 (可能 API 限流)".format(repo))
        time.sleep(1)
    
    all_urls = list(set(all_urls))
    save_cached_urls(all_urls)
    print("總共快取: {0} 個 URL".format(len(all_urls)))
    return all_urls

def get_shared_downloaded():
    if SHARED_DOWNLOAD_LOG.exists():
        with open(SHARED_DOWNLOAD_LOG, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_shared_downloaded(url):
    with open(SHARED_DOWNLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(url + "\n")

class APIKeyManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_index = 0
        self.usage_count = [0] * len(api_keys)
        self.cooldown_until = [0] * len(api_keys)
    def get_current_key(self):
        now = time.time()
        if self.cooldown_until[self.current_index] > now:
            self.switch_to_next()
            return self.get_current_key()
        return self.api_keys[self.current_index]
    def switch_to_next(self):
        start_index = self.current_index
        for _ in range(len(self.api_keys)):
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            now = time.time()
            if self.cooldown_until[self.current_index] <= now:
                return
        self.current_index = start_index
    def mark_rate_limit(self, retry_after=60):
        self.cooldown_until[self.current_index] = time.time() + retry_after
        self.usage_count[self.current_index] = 0
        self.switch_to_next()
    def mark_success(self):
        self.usage_count[self.current_index] += 1

class Pipeline:
    def __init__(self, api_name):
        self.api_name = api_name
        self.done_file = Path("done_" + api_name + ".txt")
        self.log_file = Path("pipeline_" + api_name + "_log.txt")
        self.temp_dir = Path("temp_" + api_name)
        self.temp_dir.mkdir(exist_ok=True)
        if api_name == "groq":
            self.manager = APIKeyManager([k for k in [GROQ_KEY] if k])
        elif api_name == "mistral":
            self.manager = APIKeyManager([k for k in [MISTRAL_KEY] if k])
        elif api_name == "gemini":
            self.manager = APIKeyManager([k for k in [GEMINI_KEY] if k])
        elif api_name == "ollama":
            self.manager = APIKeyManager([OLLAMA_URL] if OLLAMA_URL else [])
        self.all_urls = []
        self.processed_count = 0

    def log(self, msg):
        print(msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def load_done(self):
        if self.done_file.exists():
            with open(self.done_file, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def mark_done(self, url):
        with open(self.done_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")

    def save_entry(self, entry):
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        for attempt in range(20):
            try:
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())
                return True
            except PermissionError:
                if attempt < 19:
                    time.sleep(0.5)
                else:
                    self.log("寫入失敗: 檔案被鎖定")
            except Exception as e:
                if attempt < 19:
                    time.sleep(0.3)
                else:
                    self.log("寫入失敗: {0}".format(e))
        return False

    def download_file(self, url):
        fname = Path(urllib.parse.urlparse(url).path).name
        if not fname.endswith(".blend"):
            fname += ".blend"
        fname = urllib.parse.unquote(fname)
        
        shared_path = SHARED_DOWNLOADS_DIR / fname
        if shared_path.exists() and shared_path.stat().st_size > 1000:
            print("  [已存在，跳過下載]")
            return shared_path
        
        shared_downloaded = get_shared_downloaded()
        if url in shared_downloaded:
            print("  [已存在，跳過下載]")
            return shared_path
        
        lock_file = SHARED_DOWNLOADS_DIR / (fname + ".lock")
        if lock_file.exists():
            print("  [其他程序在下載中，等待...]")
            for _ in range(60):
                time.sleep(1)
                if shared_path.exists():
                    print("  [下載完成]")
                    return shared_path
                if not lock_file.exists():
                    break
            if not shared_path.exists():
                lock_file.unlink()
        
        tmp_path = self.temp_dir / fname
        try:
            with open(lock_file, "w") as lf:
                lf.write(url)
            encoded_url = urllib.parse.quote(url, safe=':/?&=#')
            req = urllib.request.Request(encoded_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(tmp_path, "wb") as out:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int(100 * downloaded / total_size)
                            bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                            print("\r  下載中 [{0}] {1}% ({2}/{3} KB)".format(bar, pct, downloaded // 1024, total_size // 1024), end="", flush=True)
                print()
                if downloaded < 1000:
                    tmp_path.unlink()
                    lock_file.unlink()
                    return None
                shutil.copy2(tmp_path, shared_path)
                mark_shared_downloaded(url)
                lock_file.unlink()
                return shared_path
        except Exception as e:
            print()
            self.log("下載失敗: {0}".format(e))
            try:
                lock_file.unlink()
            except:
                pass
            return None

    def extract_nodes(self, blend_path):
        script = '''
import bpy, json, sys, os
output_json = r"{output_json}"
blend_file = r"{blend_file}"
results = []
try:
    bpy.ops.wm.open_mainfile(filepath=blend_file)
except Exception as e:
    print("OPEN_ERROR:" + str(e))
    sys.exit(1)

print("FILE_LOADED:" + blend_file)
print("NODE_GROUPS_COUNT:" + str(len(bpy.data.node_groups)))

for ng in bpy.data.node_groups:
    print("NG_TYPE:" + ng.type + ":" + ng.name)

def tree_to_python(tree):
    lines = ["import bpy", "from bpy import data as bpy.data", "", "def create_node_tree():", "    tree = bpy.data.node_groups.new('" + tree.name.replace("'", "\\'") + "', 'GeometryNodeTree')"]
    for n in tree.nodes:
        if n.type == "REROUTE": continue
        node_name = "node_" + n.name.replace(" ", "_").replace("-", "_")
        lines.append("    " + node_name + " = tree.nodes.new('" + n.type + "')")
        lines.append("    " + node_name + ".location = (" + str(n.location.x) + ", " + str(n.location.y) + ")")
        if hasattr(n, 'inputs'):
            for i, inp in enumerate(n.inputs):
                if inp.is_multi_input:
                    for sock in inp.interface.items_tree:
                        if hasattr(sock, 'default_value'):
                            try:
                                lines.append("    " + node_name + ".inputs[" + str(i) + "].default_value = " + str(sock.default_value))
                            except:
                                pass
                elif hasattr(inp, 'default_value') and str(inp.default_value) != "<bpy_prop Array [0.0]>":
                    try:
                        val = inp.default_value
                        if hasattr(val, '__iter__') and not isinstance(val, str):
                            val = list(val)
                        lines.append("    " + node_name + ".inputs[" + str(i) + "].default_value = " + str(val))
                    except:
                        pass
    for link in tree.links:
        fv = link.from_socket.node.name if link.from_socket.node.type != "REROUTE" else None
        tv = link.to_socket.node.name if link.to_socket.node.type != "REROUTE" else None
        if fv and tv:
            fn = "node_" + fv.replace(" ", "_").replace("-", "_")
            tn = "node_" + tv.replace(" ", "_").replace("-", "_")
            lines.append("    links.new(" + fn + ".outputs[\"" + link.from_socket.name + "\"], " + tn + ".inputs[\"" + link.to_socket.name + "\"])")
    lines += ["", "    return tree", "", "create_node_tree()"]
    return "\\n".join(lines)

def summarize(tree):
    nt = {{}}
    for n in tree.nodes:
        nt[n.type] = nt.get(n.type, 0) + 1
    return {{"node_count": len(tree.nodes), "link_count": len(tree.links), "node_types": nt, "has_animation": any(n.type == "INPUT_SCENE_TIME" for n in tree.nodes), "has_noise": any("NOISE" in n.type for n in tree.nodes), "has_instancing": any(n.type == "INSTANCE_ON_POINTS" for n in tree.nodes), "has_distribution": any(n.type == "DISTRIBUTE_POINTS_ON_FACES" for n in tree.nodes), "has_math": any(n.type == "MATH" for n in tree.nodes), "has_material": any(n.type == "SET_MATERIAL" for n in tree.nodes)}}

found = 0
for ng in bpy.data.node_groups:
    if ng.type != "GEOMETRY": continue
    if len(ng.nodes) < 3: continue
    try:
        results.append({{"tree_name": ng.name, "summary": summarize(ng), "python_code": tree_to_python(ng)}})
        found += 1
        print("FOUND_GN:" + ng.name)
    except: pass

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
print("EXTRACTED:" + str(found))
'''.format(output_json=str(blend_path.with_suffix('.json')), blend_file=str(blend_path))
        
        with open(self.temp_dir / "extract_nodes.py", "w", encoding="utf-8") as f:
            f.write(script)
        try:
            cmd = [BLENDER_EXE, "--background", "--python", str(self.temp_dir / "extract_nodes.py"), "--"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace")
            
            debug_info = []
            for line in result.stdout.splitlines():
                if line.startswith("EXTRACTED:"):
                    count = int(line.split(":")[1])
                    self.log("  Blender 解析完成，找到 {0} 個節點樹".format(count))
                    json_path = blend_path.with_suffix('.json')
                    if count > 0 and json_path.exists():
                        with open(json_path, "r", encoding="utf-8") as f:
                            trees = json.load(f)
                        return trees
                    return []
                elif line.startswith("OPEN_ERROR:"):
                    self.log("  Blender 打開檔案失敗: {0}".format(line.split(":", 1)[1]))
                    return []
                elif line.startswith("FILE_LOADED:") or line.startswith("NODE_GROUPS_COUNT:") or line.startswith("NG_TYPE:") or line.startswith("FOUND_GN:"):
                    debug_info.append(line)
            
            for dbg in debug_info:
                self.log("  DEBUG: {0}".format(dbg))
            
            if not debug_info:
                self.log("  Blender 無輸出")
                self.log("  STDERR: {0}".format(result.stderr[:500] if result.stderr else ""))
            else:
                self.log("  Blender 未找到幾何節點樹")
            return []
        except subprocess.TimeoutExpired:
            self.log("  Blender 執行逾時 (180秒)")
            return []
        except Exception as e:
            self.log("  Blender 錯誤: {0}".format(e))
            return []
        finally:
            try:
                (self.temp_dir / "extract_nodes.py").unlink()
            except: pass

    def build_prompt(self, tree_name, summary):
        features = []
        if summary.get("has_animation"): features.append("時間驅動動畫")
        if summary.get("has_noise"): features.append("噪波紋理")
        if summary.get("has_instancing"): features.append("實例化物件")
        if summary.get("has_distribution"): features.append("表面點分佈")
        if summary.get("has_math"): features.append("數學運算")
        if summary.get("has_material"): features.append("材質指定")
        nt_str = ", ".join("{0}*{1}".format(k, v) for k, v in list(summary.get("node_types", {}).items())[:10])
        feat_str = "、".join(features) if features else "基礎幾何"
        prompt = """你是 Blender 幾何節點專家。

以下是一個 Blender 幾何節點樹的摘要：
- 名稱：{0}
- 節點數：{1}，連線數：{2}
- 功能特徵：{3}
- 節點類型：{4}

請用繁體中文寫一段描述（30-60字），格式像用戶下指令，例如「在物體表面隨機分佈球體，並讓它們隨時間上下浮動」。""".format(
            tree_name,
            summary.get('node_count', '?'),
            summary.get('link_count', '?'),
            feat_str,
            nt_str
        )
        return prompt

    def call_api(self, prompt, retries=5, base_delay=5):
        import requests
        for attempt in range(retries):
            try:
                api_key = self.manager.get_current_key()
                if not api_key:
                    self.log("  錯誤：未設定 API Key")
                    return None
                if self.api_name == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    data = {"model": "llama-3.3-8b-instant", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                elif self.api_name == "mistral":
                    url = "https://api.mistral.ai/v1/chat/completions"
                    data = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                elif self.api_name == "gemini":
                    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
                    data = {"model": "gemini-2.0-flash", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                elif self.api_name == "ollama":
                    url = "{0}/api/chat".format(OLLAMA_URL.rstrip("/"))
                    data = {"model": "llama3.2:1b", "messages": [{"role": "user", "content": prompt}], "stream": False}
                    headers = {"Content-Type": "application/json"}
                    resp = requests.post(url, json=data, headers=headers, timeout=60)
                    if resp.status_code == 200:
                        return resp.json().get("message", {}).get("content", "").strip()
                    else:
                        self.log("  API 錯誤 {0}: {1}".format(resp.status_code, resp.text[:100]))
                        return None
                headers = {"Authorization": "Bearer {0}".format(api_key), "Content-Type": "application/json"}
                resp = requests.post(url, json=data, headers=headers, timeout=30)
                if resp.status_code == 200:
                    self.manager.mark_success()
                    return resp.json()["choices"][0]["message"]["content"].strip()
                elif resp.status_code == 429:
                    self.manager.mark_rate_limit(60)
                    wait_time = base_delay * (2 ** attempt)
                    self.log("  API 限流，等待 {0} 秒...".format(wait_time))
                    time.sleep(wait_time)
                else:
                    self.log("  API 錯誤 {0}: {1}".format(resp.status_code, resp.text[:100]))
                    return None
            except Exception as e:
                self.log("  API 錯誤: {0}".format(e))
                if attempt < retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
        return None

    def run(self):
        print("=" * 60)
        print("Blender 訓練資料流水線 - {0}".format(self.api_name.upper()))
        print("=" * 60)
        print("Blender 路徑: {0}".format(BLENDER_EXE))
        print()
        done_urls = self.load_done()
        shared_downloaded = get_shared_downloaded()
        print("已處理過: {0} 個 URL".format(len(done_urls)))
        print("已下載過: {0} 個 URL (共享)".format(len(shared_downloaded)))
        print("動態獲取 URL 中...")
        self.all_urls = fetch_all_urls()
        
        pending_urls = []
        for url in self.all_urls:
            if url in done_urls:
                continue
            if url not in shared_downloaded:
                pending_urls.append(url)
        
        print("本次待下載: {0} 個 URL".format(len(pending_urls)))
        print("本次待處理: {0} 個 URL".format(len([u for u in self.all_urls if u not in done_urls])))
        print()
        
        for url in pending_urls:
            print("下載: {0}".format(url))
            blend_path = self.download_file(url)
            if not blend_path:
                self.mark_done(url)
                continue
            print("處理: {0}".format(url))
            trees = self.extract_nodes(blend_path)
            try:
                blend_path.with_suffix('.json').unlink()
            except: pass
            if not trees:
                self.mark_done(url)
                continue
            for tree in trees:
                tree_name = tree.get("tree_name", "Unnamed")
                summary = tree.get("summary", {})
                python_code = tree.get("python_code", "")
                print("  節點樹: {0} ({1} nodes)".format(tree_name, summary.get('node_count', 0)))
                desc = self.call_api(self.build_prompt(tree_name, summary))
                if desc:
                    print("  描述: {0}...".format(desc[:50]))
                    entry = {"instruction": desc, "output": python_code, "metadata": {"source_url": url, "tree_name": tree_name, "node_count": summary.get("node_count", 0)}}
                    if self.save_entry(entry):
                        self.processed_count += 1
                        print("  已儲存! 總計: {0}".format(self.processed_count))
                else:
                    print("  描述生成失敗")
                time.sleep(2)
            self.mark_done(url)
        
        remaining_urls = [u for u in self.all_urls if u not in done_urls and u in shared_downloaded]
        if remaining_urls:
            print()
            print("處理共享下載的檔案...")
            for url in remaining_urls:
                fname = Path(urllib.parse.urlparse(url).path).name
                if not fname.endswith(".blend"):
                    fname += ".blend"
                fname = urllib.parse.unquote(fname)
                blend_path = SHARED_DOWNLOADS_DIR / fname
                if not blend_path.exists():
                    continue
                print("處理: {0}".format(url))
                trees = self.extract_nodes(blend_path)
                try:
                    blend_path.with_suffix('.json').unlink()
                except: pass
                if not trees:
                    self.mark_done(url)
                    continue
                for tree in trees:
                    tree_name = tree.get("tree_name", "Unnamed")
                    summary = tree.get("summary", {})
                    python_code = tree.get("python_code", "")
                    print("  節點樹: {0} ({1} nodes)".format(tree_name, summary.get('node_count', 0)))
                    desc = self.call_api(self.build_prompt(tree_name, summary))
                    if desc:
                        print("  描述: {0}...".format(desc[:50]))
                        entry = {"instruction": desc, "output": python_code, "metadata": {"source_url": url, "tree_name": tree_name, "node_count": summary.get("node_count", 0)}}
                        if self.save_entry(entry):
                            self.processed_count += 1
                            print("  已儲存! 總計: {0}".format(self.processed_count))
                    else:
                        print("  描述生成失敗")
                    time.sleep(2)
                self.mark_done(url)
        
        print()
        print("完成! 總共儲存: {0}".format(self.processed_count))

if __name__ == "__main__":
    api_name = sys.argv[1] if len(sys.argv) > 1 else "groq"
    p = Pipeline(api_name)
    p.run()
