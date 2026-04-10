# -*- coding: utf-8 -*-
import os, sys, json, time, shutil, subprocess, urllib.request, urllib.parse, msvcrt
from pathlib import Path

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
OUTPUT_FILE = Path("./training_dataset.jsonl")

GROQ_KEY = os.environ.get("GROQ_KEY", "")
MISTRAL_KEY = os.environ.get("MISTRAL_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY", "")

HEADERS = {"User-Agent": "Mozilla/5.0"}

REPOS_TO_SCAN = [
    "BradyAJohnston/MolecularNodes",
    "node-dojo/dojo-recursive-bins",
    "cgvirus/blender-geometry-nodes-collection",
    "al1brn/geonodes",
    "vevenom/pytorchgeonodes",
    "rbarbosa51/GeometryNodesByTutorials",
    "Rideu/generative-blender",
    "IRCSS/Blender-Geometry-Node-French-Houses",
    "IRCSS/Trees-With-Geometry-Nodes-Blender",
    "IRCSS/Procedural-Chinese-Landscape-Painting-Blender-3D",
    "RanmanEmpire/RM_SubdivisionSurface",
    "RanmanEmpire/RM_CurveMorph",
    "fletchgraham/fletchnodes",
    "Tams3d/T3D-GN-Presets",
]

BLENDER_DEMO_URLS = [
    "https://download.blender.org/demo/geometry-nodes/chocolate.blend",
    "https://download.blender.org/demo/geometry-nodes/cubic-whirlpool_geometry-nodes-demo.blend",
    "https://download.blender.org/demo/geometry-nodes/field_at_index.blend",
    "https://download.blender.org/demo/geometry-nodes/flower_scattering.blend",
    "https://download.blender.org/demo/geometry-nodes/food_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/instance_attribtues.blend",
    "https://download.blender.org/demo/geometry-nodes/accumulate_field.blend",
    "https://download.blender.org/demo/geometry-nodes/ball-in-grass_geometry-nodes-demo.blend",
    "https://download.blender.org/demo/geometry-nodes/SDF_mixer_kitbukoros.blend",
    "https://download.blender.org/demo/geometry-nodes/abstract_monkey_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/procedural_vine.blend",
    "https://download.blender.org/demo/geometry-nodes/scatter_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/hair_strands.blend",
    "https://download.blender.org/demo/geometry-nodes/ocean_waves.blend",
    "https://download.blender.org/demo/geometry-nodes/city_generator.blend",
    "https://download.blender.org/demo/geometry-nodes/terrain_gen.blend",
    "https://download.blender.org/demo/test/splash.blend",
    "https://download.blender.org/demo/test/test.blend",
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
    except Exception as e:
        print(f"  獲取 {repo} 失敗: {e}")
    return urls

def fetch_all_urls():
    all_urls = list(BLENDER_DEMO_URLS)
    print("從 GitHub 倉庫搜索 blend 檔案...")
    for repo in REPOS_TO_SCAN:
        urls = fetch_blend_urls_from_repo(repo)
        if urls:
            print(f"  {repo}: 找到 {len(urls)} 個 blend 檔")
            all_urls.extend(urls)
        time.sleep(0.5)
    return list(set(all_urls))

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
        self.lock_file = Path("pipeline_" + api_name + ".lock")
        self.temp_dir = Path("temp_" + api_name)
        self.temp_dir.mkdir(exist_ok=True)
        if api_name == "groq":
            self.manager = APIKeyManager([k for k in [GROQ_KEY] if k])
        elif api_name == "mistral":
            self.manager = APIKeyManager([k for k in [MISTRAL_KEY] if k])
        else:
            self.manager = APIKeyManager([k for k in [DEEPSEEK_KEY] if k])
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
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    for _ in range(300):
                        try:
                            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 0)
                            break
                        except:
                            time.sleep(0.1)
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 0)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    self.log(f"寫入失敗: {e}")
        return False

    def download_file(self, url):
        fname = Path(urllib.parse.urlparse(url).path).name
        if not fname.endswith(".blend"):
            fname += ".blend"
        fname = urllib.parse.unquote(fname)
        tmp_path = self.temp_dir / fname
        try:
            encoded_url = urllib.parse.quote(url, safe=':/?&=#')
            req = urllib.request.Request(encoded_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(tmp_path, "wb") as out:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                if downloaded < 1000:
                    tmp_path.unlink()
                    return None
                return tmp_path
        except Exception as e:
            self.log(f"下載失敗: {e}")
            return None

    def extract_nodes(self, blend_path):
        script = '''
import bpy, json, sys
output_json = r"{output_json}"
results = []
def tree_to_python(tree):
    lines = ["import bpy", "from bpy import data as bpy.data", "", "def create_node_tree():", "    tree = bpy.data.node_groups.new('" + tree.name + "', 'GeometryNodeTree')"]
    for n in tree.nodes:
        if n.type == "REROUTE": continue
        lines.append("    " + n.name + " = tree.nodes.new('" + n.type + "')")
        lines.append("    " + n.name + ".location = (" + str(n.location.x) + ", " + str(n.location.y) + ")")
        if hasattr(n, 'inputs'):
            for i, inp in enumerate(n.inputs):
                if inp.is_multi_input:
                    for sock in inp.interface.items_tree:
                        if hasattr(sock, 'default_value'):
                            try: lines.append("    " + n.name + ".inputs[" + str(i) + "].default_value = " + str(sock.default_value))
                            except: pass
                elif hasattr(inp, 'default_value') and str(inp.default_value) != "<bpy_prop Array [0.0]>":
                    try: val = inp.default_value if not hasattr(inp.default_value, '__iter__') else list(inp.default_value)
                            lines.append("    " + n.name + ".inputs[" + str(i) + "].default_value = " + str(val))
                    except: pass
    for link in tree.links:
        fv = link.from_socket.node.name if link.from_socket.node.type != "REROUTE" else None
        tv = link.to_socket.node.name if link.to_socket.node.type != "REROUTE" else None
        if fv and tv:
            lines.append("    links.new(" + fv + ".outputs[\"" + link.from_socket.name + "\"], " + tv + ".inputs[\"" + link.to_socket.name + "\"])")
    lines += ["", "    return tree", "", "create_node_tree()"]
    return "\\n".join(lines)
def summarize(tree):
    nt = {{}}
    for n in tree.nodes:
        nt[n.type] = nt.get(n.type, 0) + 1
    return {{"node_count": len(tree.nodes), "link_count": len(tree.links), "node_types": nt, "has_animation": any(n.type == "INPUT_SCENE_TIME" for n in tree.nodes), "has_noise": any("NOISE" in n.type for n in tree.nodes), "has_instancing": any(n.type == "INSTANCE_ON_POINTS" for n in tree.nodes), "has_distribution": any(n.type == "DISTRIBUTE_POINTS_ON_FACES" for n in tree.nodes), "has_math": any(n.type == "MATH" for n in tree.nodes), "has_material": any(n.type == "SET_MATERIAL" for n in tree.nodes)}}
for ng in bpy.data.node_groups:
    if ng.type != "GEOMETRY": continue
    if len(ng.nodes) < 3: continue
    try:
        results.append({{"tree_name": ng.name, "summary": summarize(ng), "python_code": tree_to_python(ng)}})
    except: pass
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
print("EXTRACTED:{{0}}".format(len(results)))
'''.format(output_json=str(blend_path.with_suffix('.json')))
        with open(self.temp_dir / "extract_nodes.py", "w", encoding="utf-8") as f:
            f.write(script)
        try:
            cmd = [BLENDER_EXE, "--background", "--python", str(self.temp_dir / "extract_nodes.py"), "--", str(blend_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace")
            for line in result.stdout.splitlines():
                if line.startswith("EXTRACTED:"):
                    count = int(line.split(":")[1])
                    self.log(f"  Blender 解析完成，找到 {count} 個節點樹")
                    json_path = blend_path.with_suffix('.json')
                    if count > 0 and json_path.exists():
                        with open(json_path, "r", encoding="utf-8") as f:
                            trees = json.load(f)
                        return trees
                    return []
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
                    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                elif self.api_name == "mistral":
                    url = "https://api.mistral.ai/v1/chat/completions"
                    data = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                else:
                    url = "https://api.deepseek.com/chat/completions"
                    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                headers = {"Authorization": f"Bearer {{api_key}}", "Content-Type": "application/json"}
                resp = requests.post(url, json=data, headers=headers, timeout=30)
                if resp.status_code == 200:
                    self.manager.mark_success()
                    return resp.json()["choices"][0]["message"]["content"].strip()
                elif resp.status_code == 429:
                    self.manager.mark_rate_limit(60)
                    wait_time = base_delay * (2 ** attempt)
                    self.log(f"  API 限流，等待 {{wait_time}} 秒...")
                    time.sleep(wait_time)
                else:
                    self.log(f"  API 錯誤 {{resp.status_code}}: {{resp.text[:100]}}")
                    return None
            except Exception as e:
                self.log(f"  API 錯誤: {{e}}")
                if attempt < retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
        return None

    def run(self):
        print("=" * 60)
        print(f"Blender 訓練資料流水線 - {self.api_name.upper()}")
        print("=" * 60)
        print(f"Blender 路徑: {BLENDER_EXE}")
        print()
        done_urls = self.load_done()
        print(f"已處理過: {len(done_urls)} 個 URL")
        print("動態獲取 URL 中...")
        self.all_urls = fetch_all_urls()
        print(f"總共發現: {len(self.all_urls)} 個 URL")
        pending_urls = [u for u in self.all_urls if u not in done_urls]
        print(f"本次待處理: {len(pending_urls)} 個 URL")
        print()
        for url in pending_urls:
            print(f"處理: {url}")
            blend_path = self.download_file(url)
            if not blend_path:
                self.mark_done(url)
                continue
            trees = self.extract_nodes(blend_path)
            try:
                blend_path.unlink()
                blend_path.with_suffix('.json').unlink()
            except: pass
            if not trees:
                self.mark_done(url)
                continue
            for tree in trees:
                tree_name = tree.get("tree_name", "Unnamed")
                summary = tree.get("summary", {})
                python_code = tree.get("python_code", "")
                print(f"  節點樹: {tree_name} ({summary.get('node_count', 0)} nodes)")
                desc = self.call_api(self.build_prompt(tree_name, summary))
                if desc:
                    print(f"  描述: {desc[:50]}...")
                    entry = {"instruction": desc, "output": python_code, "metadata": {"source_url": url, "tree_name": tree_name, "node_count": summary.get("node_count", 0)}}
                    if self.save_entry(entry):
                        self.processed_count += 1
                        print(f"  已儲存! 總計: {self.processed_count}")
                else:
                    print("  描述生成失敗")
                time.sleep(2)
            self.mark_done(url)
        print()
        print(f"完成! 總共儲存: {self.processed_count}")

if __name__ == "__main__":
    api_name = sys.argv[1] if len(sys.argv) > 1 else "groq"
    p = Pipeline(api_name)
    p.run()
