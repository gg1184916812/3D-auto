# -*- coding: utf-8 -*-
import os, sys, json, time, shutil, subprocess, urllib.request, urllib.parse, msvcrt
from pathlib import Path

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
OUTPUT_FILE = Path("./training_dataset.jsonl")

GROQ_KEYS = [os.environ.get("GROQ_KEY", "")]
MISTRAL_KEYS = [os.environ.get("MISTRAL_KEY", "")]
DEEPSEEK_KEYS = [os.environ.get("DEEPSEEK_KEY", "")]

HEADERS = {"User-Agent": "Mozilla/5.0"}

BLENDER_OFFICIAL = [
    "https://download.blender.org/demo/geometry-nodes/4D_Gaussian_Splatting-Nunchucks_and_cat.blend",
    "https://download.blender.org/demo/geometry-nodes/SDF_mixer_kitbukoros.blend",
    "https://download.blender.org/demo/geometry-nodes/abstract_monkey_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/accumulate_field.blend",
    "https://download.blender.org/demo/geometry-nodes/ball-in-grass_geometry-nodes_demo.blend",
]

SPACE_UNIVERSE = [
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Space/Galaxy/crunch.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Space/Nebulator/Nebulator.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Space/Nebulator/nebulav2.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Space/Galaxy/shadegalaxy%20%5B2.8%5D.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Space/Nebulator/Nebulator%20%5Bold%5D.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Planets/Planetator/planetgen%20%5B2.8%5D.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Planets/Planetator/planetgen%20%5Belder%5D.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Planets/Ground/ground_mastering.blend",
    "https://raw.githubusercontent.com/Rideu/generative-blender/HEAD/Planets/Ground/groundsloping_mastering.blend",
]

DEEPSEEK_URLS = [
    "https://download.blender.org/demo/geometry-nodes/chocolate.blend",
    "https://download.blender.org/demo/geometry-nodes/cubic-whirlpool_geometry-nodes-demo.blend",
    "https://download.blender.org/demo/geometry-nodes/field_at_index.blend",
    "https://download.blender.org/demo/geometry-nodes/flower_scattering.blend",
    "https://download.blender.org/demo/geometry-nodes/food_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/instance_attribtues.blend",
    "https://download.blender.org/demo/geometry-nodes/accumulate_field.blend",
    "https://download.blender.org/demo/geometry-nodes/ball-in-grass_geometry-nodes_demo.blend",
    "https://download.blender.org/demo/geometry-nodes/SDF_mixer_kitbukoros.blend",
    "https://download.blender.org/demo/geometry-nodes/abstract_monkey_geometry-nodes_demo.blend",
    "https://raw.githubusercontent.com/BradyAJohnston/MolecularNodes/HEAD/molecularnodes/assets/node_data_file.blend",
    "https://raw.githubusercontent.com/node-dojo/dojo-recursive-bins/HEAD/Dojo%20Bin%20Generator_recursive%202%20step_v0.1.1.blend",
    "https://raw.githubusercontent.com/BlenderDev/blender-geometry-nodes/HEAD/examples/sphere_packing.blend",
    "https://raw.githubusercontent.com/BlenderDev/blender-geometry-nodes/HEAD/examples/instancing.blend",
    "https://raw.githubusercontent.com/BlenderDev/blender-geometry-nodes/HEAD/examples/noise_displacement.blend",
]

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
            self.manager = APIKeyManager(GROQ_KEYS)
            self.urls = BLENDER_OFFICIAL
        elif api_name == "mistral":
            self.manager = APIKeyManager(MISTRAL_KEYS)
            self.urls = SPACE_UNIVERSE
        else:
            self.manager = APIKeyManager(DEEPSEEK_KEYS)
            self.urls = DEEPSEEK_URLS
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
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            try:
                for _ in range(300):
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 0)
                        break
                    except:
                        time.sleep(0.1)
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 0)
            except:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
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
                data = b""
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    data += chunk
                    if total_size > 0:
                        pct = min(100, downloaded * 100 // total_size)
                        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                        print("\r  下載中 [{0}] {1}% ({2}KB)".format(bar, pct, downloaded//1024), end="", flush=True)
            print()
            if not data[:7].startswith(b"BLENDER"):
                self.log("  不是有效的 BLEND 檔案")
                return None
            with open(tmp_path, "wb") as f:
                f.write(data)
            size_mb = tmp_path.stat().st_size / 1024 / 1024
            self.log("  下載完成: {0} ({1:.1f}MB)".format(fname, size_mb))
            return tmp_path
        except Exception as e:
            self.log("  下載失敗: {0}".format(e))
            return None
    
    def extract_nodes(self, blend_path):
        self.log("  正在用 Blender 解析節點...")
        output_json = self.temp_dir / "extracted.json"
        script_path = self.temp_dir / "_extract.py"
        script = r'''import bpy, json, sys
blend_file = sys.argv[sys.argv.index("--") + 1]
output_json = sys.argv[sys.argv.index("--") + 2]
bpy.ops.wm.open_mainfile(filepath=blend_file)
results = []
def get_socket_info(socket):
    info = {"name": socket.name, "type": socket.type}
    try:
        if socket.is_linked:
            info["is_linked"] = True
        else:
            info["is_linked"] = False
            dv = socket.default_value
            if dv is None: pass
            elif hasattr(dv, "__iter__") and not isinstance(dv, str):
                info["default_value"] = [round(x, 6) if isinstance(x, float) else x for x in dv]
            elif isinstance(dv, (int, float, bool, str)):
                info["default_value"] = round(dv, 6) if isinstance(dv, float) else dv
    except: pass
    return info
def tree_to_python(tree):
    lines = ["import bpy", "", "def create_node_tree():"]
    lines.append("    tree = bpy.data.node_groups.new(name=\"{0}\", type=\"GeometryNodeTree\")".format(tree.name))
    lines += ["    nodes = tree.nodes", "    links = tree.links", "    nodes.clear()", ""]
    name_map = {}
    lines.append("    # nodes")
    for i, node in enumerate(tree.nodes):
        v = "n{0}".format(i)
        name_map[node.name] = v
        lines.append("    {0} = nodes.new(\"{1}\")".format(v, node.bl_idname))
        lines.append("    {0}.name = \"{1}\"".format(v, node.name))
        lines.append("    {0}.location = ({1}, {2})".format(v, int(node.location.x), int(node.location.y)))
        if node.label:
            lines.append("    {0}.label = \"{1}\"".format(v, node.label))
        for inp in node.inputs:
            if not inp.is_linked and hasattr(inp, "default_value"):
                try:
                    dv = inp.default_value
                    if hasattr(dv, "__iter__") and not isinstance(dv, str):
                        dv_str = [round(x,4) if isinstance(x,float) else x for x in dv]
                        lines.append("    {0}.inputs[\"{1}\"].default_value = {2}".format(v, inp.name, dv_str))
                    elif isinstance(dv, float):
                        lines.append("    {0}.inputs[\"{1}\"].default_value = {2}".format(v, inp.name, round(dv,4)))
                    elif isinstance(dv, (bool, int)):
                        lines.append("    {0}.inputs[\"{1}\"].default_value = {2}".format(v, inp.name, dv))
                except: pass
        lines.append("")
    lines.append("    # links")
    for link in tree.links:
        fv = name_map.get(link.from_node.name)
        tv = name_map.get(link.to_node.name)
        if fv and tv:
            lines.append("    links.new({0}.outputs[\"{1}\"], {2}.inputs[\"{3}\"])".format(fv, link.from_socket.name, tv, link.to_socket.name))
    lines += ["", "    return tree", "", "create_node_tree()"]
    return "\n".join(lines)
def summarize(tree):
    nt = {}
    for n in tree.nodes:
        nt[n.type] = nt.get(n.type, 0) + 1
    return {"node_count": len(tree.nodes), "link_count": len(tree.links), "node_types": nt, "has_animation": any(n.type == "INPUT_SCENE_TIME" for n in tree.nodes), "has_noise": any("NOISE" in n.type for n in tree.nodes), "has_instancing": any(n.type == "INSTANCE_ON_POINTS" for n in tree.nodes), "has_distribution": any(n.type == "DISTRIBUTE_POINTS_ON_FACES" for n in tree.nodes), "has_math": any(n.type == "MATH" for n in tree.nodes), "has_material": any(n.type == "SET_MATERIAL" for n in tree.nodes)}
for ng in bpy.data.node_groups:
    if ng.type != "GEOMETRY": continue
    if len(ng.nodes) < 3: continue
    try:
        results.append({"tree_name": ng.name, "summary": summarize(ng), "python_code": tree_to_python(ng)})
    except: pass
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)
print("EXTRACTED:{0}".format(len(results)))
'''
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        try:
            cmd = [BLENDER_EXE, "--background", "--python", str(script_path), "--", str(blend_path), str(output_json)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace")
            for line in result.stdout.splitlines():
                if line.startswith("EXTRACTED:"):
                    count = int(line.split(":")[1])
                    self.log("  Blender 解析完成，找到 {0} 個節點樹".format(count))
                    if count > 0 and output_json.exists():
                        with open(output_json, "r", encoding="utf-8") as f:
                            trees = json.load(f)
                        return trees
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
                script_path.unlink()
                output_json.unlink()
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
                if self.api_name == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    data = {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                elif self.api_name == "mistral":
                    url = "https://api.mistral.ai/v1/chat/completions"
                    data = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                else:
                    url = "https://api.deepseek.com/v1/chat/completions"
                    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
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
        print("已處理過: {0} 個 URL".format(len(done_urls)))
        print("本次任務: {0} 個 URL".format(len(self.urls)))
        print()
        for url in self.urls:
            if url in done_urls:
                print("跳過 (已處理): {0}".format(url))
                continue
            print()
            print("處理: {0}".format(url))
            blend_path = self.download_file(url)
            if not blend_path:
                self.mark_done(url)
                continue
            trees = self.extract_nodes(blend_path)
            try:
                blend_path.unlink()
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
                    self.save_entry(entry)
                    self.processed_count += 1
                    print("  已儲存! 總計: {0}".format(self.processed_count))
                else:
                    print("  描述生成失敗")
                time.sleep(2)
            self.mark_done(url)
            print("進度: {0}/{1}".format(len([u for u in self.urls if u in done_urls or u == url]), len(self.urls)))
        print()
        print("完成! 總共儲存: {0}".format(self.processed_count))

if __name__ == "__main__":
    api_name = sys.argv[1] if len(sys.argv) > 1 else "groq"
    p = Pipeline(api_name)
    p.run()
