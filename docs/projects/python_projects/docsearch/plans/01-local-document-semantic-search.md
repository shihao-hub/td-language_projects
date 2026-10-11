# Plan for: 鏈湴鏂囨。涓庢妧鑳藉簱璇箟妫€绱㈢郴缁?(docsearch)

**闂闄堣堪**锛?
鐢ㄦ埛鏈湴鐩綍鍜?skill 鐩綍瀛樻湁澶ч噺鏂囨。锛屽洜鍏抽敭璇嶈蹇嗘ā绯娿€佹枃妗ｅ懡鍚嶅悇寮傦紝浼犵粺鐨勭簿纭?grep / 绾枃浠跺悕鎼滅储闅句互鏈夋晥瀹氫綅锛涘悓鏃舵枃妗ｅ湪鏃ュ父鏇存柊淇敼鍚庯紝鏈熸湜绯荤粺鑳借嚜鍔ㄩ噸璺戝缓绔嬫渶鏂扮储寮曘€傞渶瑕佷竴濂楄交閲忋€佸畬鍏ㄧ绾裤€佹敮鎸佹ā绯婅嚜鐒惰瑷€璁板繂鎼滅储鐨勬湰鍦扮郴缁燂紝骞舵敮鎸?CLI銆丣SON銆丼chema銆丠TTP API 浠ュ強鍐呭祵 WebUI銆?

**闇€姹傜‘璁?*锛?
1. **椤圭洰瀹氫綅涓庡懡鍚?*锛氱嫭绔?Python 瀛愰」鐩紝浣嶄簬 `python_projects/docsearch`锛堟棤妯潬/涓嬪垝绾挎嫾鍚堬級銆?
2. **鍒嗗眰鏋舵瀯锛堝鏍?go projects CLI 鏍囧噯锛?*锛?
   - **Service 灞?*锛氭牳蹇冧笟鍔″唴鏍革紙Markdown 鎻愬彇鍒囧潡銆丗astEmbed 璇箟鍚戦噺璁＄畻銆丩anceDB 宓屽叆寮忓悜閲忓閲忓瓨鍌ㄣ€乄atchdog 鏂囦欢绯荤粺鑷姩鐩戝惉涓庨槻鎶栭噸璺戯級銆?
   - **CLI 灞傦紙Typer锛?*锛氭敮鎸佷汉璇绘帶鍒跺彴楂樹寒杈撳嚭銆乣--json` 缁撴瀯鍖栬緭鍑恒€乣--schema` 鍗忚鎻忚堪銆傛彁渚?`watch`銆乣index`銆乣search`銆乣serve` 绛夊懡浠ゃ€?
   - **HTTP API 灞傦紙FastAPI锛?*锛氭毚闇?RESTful 鎼滅储銆佺姸鎬佺洃鎺т笌閲嶅缓绱㈠紩鎺ュ彛锛屽簳灞傜洿鎺ヨ皟鐢?Service 灞傘€?
   - **WebUI 灞?*锛氱函鍘熺敓闈欐€?HTML/CSS/JavaScript锛屽唴宓屽湪 FastAPI 闈欐€佹寕杞戒腑锛屾彁渚涙瀬绠€鍗曢〉妫€绱㈡涓庢枃妗ｉ珮浜煡鐪嬨€?
3. **閰嶇疆椹卞姩**锛氶噰鐢?`.toml` 閰嶇疆鏂囦欢锛堝 `config.toml`锛夛紝閰嶇疆鐩戝惉鐩綍娓呭崟锛堝 skills 鐩綍銆侀€氱敤鏂囨。鐩綍锛夈€佹枃浠惰繃婊よ鍒欍€佹ā鍨嬮€夊瀷鍙婂垎鍧楀弬鏁般€?
4. **鏁版嵁瀛樺偍鍚堣**锛氶伒寰埗浠?`AGENTS.md` 绾︽潫锛孡anceDB 鍚戦噺搴撲笌杩愯鏃剁紦瀛樹竴寰嬪瓨鍌ㄥ湪 `%APPDATA%\language_projects\docsearch\`锛堢己鐪佸洖閫€ `~/.language_projects/docsearch/`锛夈€?
5. **闄勫綍鎺ㄨ崘杞欢**锛氬湪璁″垝鏂囨湯鏁寸悊骞堕檮涓婃垚鐔熷紑婧愭枃妗ｆ绱笌鐭ヨ瘑搴撹蒋浠舵竻鍗曘€?

**鑳屾櫙鐜扮姸**锛?
- 鐖朵粨鏍圭洰褰曚负 Monorepo 缁撴瀯锛宍python_projects` 涓虹嫭绔?Git 妯″潡銆?
- 鏍圭洰褰曞瓨鍦ㄥぇ閲忚法璇█鏂囨。鍙婂叏灞€鎶€鑳界洰褰曪紙`D:\Users\language_projects\.agents\skills`銆乣C:\Users\29580\.gemini\config\skills` 绛夛級銆?
- 鏈哄櫒鍏峰鐜颁唬 Python 3 鐜涓?`uv` 鏀寔銆?

**鏂规鏋舵瀯**锛?
```mermaid
graph TD
    A[鐢ㄦ埛缁堢 CLI / Typer] -->|璋冪敤 / --json / --schema| S[Service 涓氬姟鍐呮牳]
    B[WebUI 娴忚鍣ㄥ崟椤礭 -->|Fetch REST API| H[FastAPI HTTP 鏈嶅姟]
    H -->|璋冪敤| S
    
    subgraph Service 鏍稿績灞?
        S --> W[Watcher 鏂囦欢鐩戝惉鍣?- watchdog]
        S --> P[Parser & Chunker 鏂囨。鍒囧潡鍣╙
        S --> E[Embedding 寮曟搸 - fastembed]
        S --> V[VectorStore 鍚戦噺搴?- LanceDB]
    end

    W -->|鏂囦欢澧炲垹鏀逛簨浠秥 P
    P --> E
    E -->|鍐欏叆鍚戦噺涓庢枃鏈瑋 V
    V -->|%APPDATA%/language_projects/docsearch/| D[(LanceDB 鏈湴鏂囦欢瀛樺偍)]
```

**浠诲姟鍒嗚В**锛?
- [x] Task 1: 鍒濆鍖?docsearch 椤圭洰楠ㄦ灦涓庨厤缃枃浠惰鑼?
  - 鏂囦欢锛歚python_projects/docsearch/pyproject.toml`, `python_projects/docsearch/src/docsearch/config.py`
  - 瀹炵幇锛氶厤缃?`pyproject.toml`锛堜緷璧?`typer`, `fastapi`, `uvicorn`, `lancedb`, `fastembed`, `watchdog` 绛夛級锛涘疄鐜板熀浜?`tomllib` 鐨勯厤缃鍙栦笌璺緞瑙ｆ瀽锛岄粯璁ゅ瓨鍌ㄨ矾寰勪弗鏍奸伒寰?`%APPDATA%\language_projects\docsearch\`銆?
  - 楠岃瘉锛氳繍琛?`uv run python -c "from docsearch.config import get_config; print(get_config())"` 姝ｇ‘瑙ｆ瀽骞跺垱寤?APPDATA 璺緞銆?
  - Demo锛氭垚鍔熺敓鎴愰粯璁?`config.toml` 妯℃澘銆?
- [x] Task 2: 瀹炵幇鏍稿績 Service 灞傦紙鍒嗗潡瑙ｆ瀽銆丗astEmbed 鍚戦噺鍖栦笌 LanceDB 澧為噺瀛樺彇锛?
  - 鏂囦欢锛歚python_projects/docsearch/src/docsearch/parser.py`, `python_projects/docsearch/src/docsearch/indexer.py`, `python_projects/docsearch/src/docsearch/service.py`
  - 瀹炵幇锛氭寜 Markdown 鏍囬鎴栨钀藉仛璇箟 chunking锛涢泦鎴?`fastembed` 鐨勪腑鏂囪交閲忔ā鍨嬶紙榛樿 `BAAI/bge-small-zh-v1.5`锛夛紱浣跨敤 LanceDB 杩涜澧為噺 upsert锛堝厛鍩轰簬 filepath 娓呯悊鍘嗗彶 chunks 鍐嶅啓鍏ユ渶鏂?chunks锛夛紱瀹炵幇娣峰悎鎴栫函鍚戦噺妫€绱紝杩斿洖鍛戒腑鏂囨。璺緞銆佽鍙疯寖鍥淬€佺浉浼煎害涓庝笂涓嬫枃鎽樿銆?
  - 楠岃瘉锛氳繍琛屾祴璇曪紝鍐欏叆妯℃嫙 Markdown 鏂囨。锛屾绱㈣嚜鐒惰瑷€鍙ュ瓙骞舵纭柇瑷€杩斿洖鏂囦欢璺緞銆?
  - Demo锛氳皟鐢?`service.search("骞跺彂閿佹帓闅?)` 鍑嗙‘瀹氫綅娴嬭瘯鏂囨。銆?
- [x] Task 3: 瀹炵幇 Watchdog 澧為噺鏂囦欢鐑洃鍚笌鑷姩闃叉姈閲嶈窇鏈哄埗
  - 鏂囦欢锛歚python_projects/docsearch/src/docsearch/watcher.py`
  - 瀹炵幇锛氬熀浜?`watchdog.observers.Observer` 鐩戝惉閰嶇疆涓０鏄庣殑鎵€鏈夌洰褰曪紙閫掑綊锛夛紱閽堝 `.md` 鍙樺姩锛堟柊寤恒€佷慨鏀广€侀噸鍛藉悕銆佸垹闄わ級寮曞叆 500ms~1s 闃叉姈瀹氭椂鍣紝鑷姩璋冪敤 Service 澧為噺閲嶈窇瀵瑰簲鍗曟枃浠剁殑鍚戦噺閲嶅缓锛涘垹闄ゆ枃浠舵椂鑷姩绾ц仈鍓旈櫎鍚戦噺銆?
  - 楠岃瘉锛氫慨鏀规寚瀹氱洰褰曚腑鐨勬祴璇?`.md`锛岃瀵熷悗鍙版棩蹇楄緭鍑哄閲忔洿鏂版彁绀哄苟楠岃瘉鏂板唴瀹圭珛鍗冲彲鏌ャ€?
  - Demo锛氫繚瀛樻枃妗ｅ悗 1 绉掑唴锛屾柊鍐呭鍗冲彲琚绱㈠懡涓€?
- [x] Task 4: 瀹炵幇 CLI 鍏ュ彛锛堝鏍?go projects CLI 瑙勮寖锛?-json銆?-schema銆佷汉璇昏緭鍑猴級
  - 鏂囦欢锛歚python_projects/docsearch/src/docsearch/cli.py`
  - 瀹炵幇锛氬熀浜?`typer` 鏋勫缓鍛戒护锛?
    - `docsearch search <query>`锛氶粯璁や汉绫诲彲璇婚珮浜墦鍗帮紱`--json` 杈撳嚭绾?JSON锛沗--schema` 杈撳嚭璇ュ懡浠ょ殑鍏ュ弬鍑哄弬 JSON Schema銆?
    - `docsearch index [--force]`锛氬叏閲忔壂鎻忛厤缃洰褰曞苟寤哄簱銆?
    - `docsearch watch`锛氬惎鍔ㄥ父椹绘枃浠剁洃鍚櫒銆?
    - `docsearch serve [--port 8000]`锛氬惎鍔?HTTP API 涓?WebUI 鏈嶅姟銆?
  - 楠岃瘉锛歚uv run docsearch search "娴嬭瘯" --schema` 鎴愬姛杈撳嚭鏈夋晥 JSON Schema锛沗--json` 杈撳嚭绗﹀悎鏍煎紡銆?
  - Demo锛氬懡浠よ鎵ц妯＄硦妫€绱紝缁堢鍛堢幇鏍煎紡鍖栨枃浠惰矾寰勪笌鏂囨湰棰勮銆?
- [x] Task 5: 瀹炵幇 FastAPI HTTP 鏈嶅姟涓庡唴宓?WebUI 鍗曢〉
  - 鏂囦欢锛歚python_projects/docsearch/src/docsearch/server.py`, `python_projects/docsearch/src/docsearch/web/index.html`, `python_projects/docsearch/src/docsearch/web/app.js`, `python_projects/docsearch/src/docsearch/web/style.css`
  - 瀹炵幇锛欶astAPI 鎻愪緵 `/api/search`銆乣/api/status`銆乣/api/reindex`锛涙寕杞芥湰鍦伴潤鎬佽祫婧愮洰褰曪紱WebUI 閲囩敤鏋佺畝鍘?AI 鍛崇殑鐜颁唬娣辨祬鑹茶嚜閫傚簲鐣岄潰锛屾敮鎸佸揩閫熸悳绱㈡銆佸疄鏃堕珮浜€佸師鏂囦欢鏈湴蹇€熻烦杞垨娈佃惤闃呰銆?
  - 楠岃瘉锛氬惎鍔ㄦ湇鍔″悗璁块棶 `http://localhost:8000`锛屾祴璇曢〉闈㈡绱笌杩斿洖浜や簰銆?
  - Demo锛氭祻瑙堝櫒鎵撳紑鎼滅储妗嗚緭鍏モ€滄ā绯婅嚜鐒惰瑷€闂鈥濓紝鍗虫椂鍒楀嚭鐩稿叧鏂囨。鐗囨涓庢枃浠跺悕銆?

---

## 闄勫綍锛氭帹鑽愮殑鎴愮啛寮€婧愭枃妗ｆ绱笌鐭ヨ瘑搴撹蒋浠?

濡傛灉浣犲湪鏈潵甯屾湜鐩存帴閫夌敤鎴愬瀷杞欢鎴栦綔涓虹敓浜х骇澶囬€夋柟妗堬紝鎺ㄨ崘浠ヤ笅鍑犳浼樼寮€婧愰」鐩細

| 寮€婧愰」鐩?| 鏍稿績瀹氫綅涓庢妧鏈爤 | 鐩綍鍙樺姩鐩戝惉鑳藉姏 | 閫傜敤鍦烘櫙涓庝寒鐐?|
| :--- | :--- | :--- | :--- |
| **[Khoj](https://github.com/khoj-ai/khoj)** | **鏈€瀹屽杽鐨勪釜浜虹绾跨浜屽ぇ鑴?*<br>Python / FastAPI + Local Embeddings + Local LLM | **鍘熺敓鏀寔鐩綍鐑洃瑙?*<br>鍚庡彴鑷姩鎵弿骞跺湪鏂囦欢澧炲垹鏀规椂鑷姩鏇存柊鍚戦噺 | 鍏峰妗岄潰绔€乄eb绔€丱bsidian 鎻掍欢涓?Emacs 鎻掍欢銆傛敮鎸?Markdown銆丳DF銆丱rg-mode锛屾敮鎸佺绾胯嚜鐒惰瑷€鎼滅储鍜岀洿鎺ュ璇濄€?|
| **[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm)** | **涓€绔欏紡妗岄潰鐭ヨ瘑搴撲笌宸ヤ綔鍖?RAG**<br>Node / LanceDB / Chromium 妗岄潰绔?| **鏀寔 Local Folder Sync**<br>鍙厤缃畾鏃舵垨鎸夐渶鍚屾鏈湴鏂囦欢澶?| 妗岄潰涓€閿畨瑁咃紝鍐呯疆鍚戦噺鏁版嵁搴撲笌杞婚噺宓屽叆妯″瀷锛岄€傚悎甯屾湜瀹屽叏涓嶇敤鍛戒护琛屻€佸吋椤炬枃妗ｆ绱笌瀹屾暣瀵硅瘽鐨勭敤鎴枫€?|
| **[qmd](https://github.com/tobi/qmd)** | **鏋佺畝楂橀€熸湰鍦?Markdown 鎼滅储寮曟搸**<br>Node / SQLite-vec / 涓撶敤杞婚噺妯″瀷 | **澧為噺 mtime 杩借釜**<br>缁撳悎 Obsidian 鎻掍欢鎴栧悗鍙拌繘绋嬪閲忓祵鍏?| 涓撲负 Markdown 鎵撻€狅紝娣峰悎妫€绱紙鍚戦噺 + BM25 鍏抽敭璇嶏級锛屾ā鍨嬩綋绉粎绾?300MB锛屾绱㈡瀬蹇€?|
| **[Smart Connections](https://github.com/brianpetro/obsidian-smart-connections)** | **Obsidian 涓撳睘璇箟妫€绱㈡彃浠?*<br>宓屽叆寮?ONNX / BGE 妯″瀷 | **娣卞害缁戝畾 Obsidian 鍐呴儴鏂囦欢绯荤粺**<br>鏂囦欢淇濆瓨鏃跺疄鏃惰绠楀祵鍏ュ悜閲?| 閫傚悎鎵€鏈夋枃妗ｅ潎鍦?Obsidian 涓鐞嗙殑鐢ㄦ埛锛屾棤缂濆湪绗旇渚ц竟鏍忓睍绀鸿涔夋渶鐩稿叧鐨勫巻鍙茬瑪璁般€?|
| **[MCP-Markdown-RAG](https://github.com/Zackriya-Solutions/MCP-Markdown-RAG)** | **闈㈠悜 Agent 鐨勬湰鍦?Markdown MCP 鏈嶅姟**<br>Python / MCP 鍗忚 / 澧為噺鍚屾鏃ュ織 | **杩借釜鏃ュ織锛圱racking Log锛夊閲忔洿鏂?*<br>鑷姩瑁佸壀鍒犻櫎鍐呭锛屼粎鏇存柊淇敼鏂囦欢 | 閫傚悎閰嶅悎 Cursor銆丆laude Code銆丄ntigravity 绛夋櫤鑳戒綋锛岄殢鏃跺皢鏈湴鐭ヨ瘑搴撴寕杞戒负鏅鸿兘浣撶殑 Tool銆?|
