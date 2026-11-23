# AI 喲不錯喔（AI-Yo Music）

給年輕創作者的 AI 音樂製作 MVP。輸入文字靈感、選擇曲風情緒與音樂長度，即可透過單頁介面取得可播放的音訊。沒有外部 API 金鑰時會使用示範模式，方便試用完整操作流程。

## 技術與功能

- Python 3.12、Flask、requests、原生 HTML/CSS/JavaScript
- Vercel Python Function，無狀態執行；不在伺服器寫入使用者作品或本機持久檔案
- `POST /api/generate` 驗證 JSON 欄位，連接外部生成 API 或回傳示範任務
- `GET /api/status/<task_id>` 輪詢非同步生成狀態
- `GET /health` 部署健康檢查
- 外部 HTTP 請求設有連線與讀取逾時，並整理逾時、HTTP、連線及 JSON 錯誤為繁體中文

## 專案結構

```text
.
├── api/index.py          # Vercel Function 入口
├── app.py                # Flask 應用與 API
├── static/css/style.css
├── static/js/app.js
├── templates/index.html
├── .env.example
├── .gitignore
├── .python-version
├── requirements.txt
└── vercel.json
```

## 環境變數

| 變數 | 必要 | 說明 |
|---|---:|---|
| `MUSIC_API_KEY` | 否 | 外部音樂 API 金鑰；僅存放於本機環境或 Vercel Environment Variables。未設定會自動使用示範模式。 |
| `MUSIC_API_BASE_URL` | 使用正式 API 時必要 | HTTPS API 根網址。MVP 預期 `POST {BASE_URL}/generate` 及 `GET {BASE_URL}/status/{task_id}`。 |
| `MOCK_MODE` | 否 | 設為 `true` 時強制使用示範音訊。預設 `false`。 |

請複製 `.env.example` 為 `.env`，在本機填入自己的值。`.env` 已加入 Git 忽略清單；不要將金鑰寫入程式碼、README 或提交至 GitHub。正式音樂 API 的回應應為 JSON。生成端點支援 `task_id`、`status`、`audio_url` 欄位（亦接受 `id`/`url`）；狀態端點回傳 `queued`、`processing`、`succeeded` 或 `failed` 及可選 `audio_url`。音訊連結必須為 HTTPS。

未設定金鑰或 `MOCK_MODE=true` 時，後端回傳公開 SoundHelix 測試音訊及示範任務 ID。這是共用示範曲，不會依提示詞產生新音樂。

## 本機啟動

安裝 Python 3.12 後，在專案根目錄執行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

開啟 <http://127.0.0.1:5000>。未設定 API 金鑰時會自動進入示範模式。健康檢查網址為 <http://127.0.0.1:5000/health>。若 PowerShell 不允許啟用虛擬環境，可直接使用 `\.venv\Scripts\python.exe` 執行安裝與啟動指令。

## 推送至 GitHub

在 GitHub 建立空白儲存庫後，於專案根目錄執行（替換成自己的儲存庫網址）：

```powershell
git init
git add .
git status
git commit -m "Build AI Yo Music MVP"
git branch -M main
git remote add origin https://github.com/<YOUR_ACCOUNT>/<YOUR_REPOSITORY>.git
git push -u origin main
```

推送前請檢查 `git status`，確認 `.env`、金鑰與 `.venv` 沒有進入提交內容。

## 部署至 Vercel

1. 登入 [Vercel](https://vercel.com/)，選擇 **Add New → Project**，匯入剛推送的 GitHub 儲存庫。
2. 保持根目錄為專案根目錄。`vercel.json` 會將所有路徑轉給 `api/index.py` Flask Function；Python 版本由 `.python-version` 指定為 3.12。
3. 在專案的 **Settings → Environment Variables** 新增 `MUSIC_API_KEY`、`MUSIC_API_BASE_URL`、`MOCK_MODE`。沒有音樂 API 時可只加入 `MOCK_MODE=true`，或不設定金鑰以自動示範模式執行。
4. 將變數套用到需要的環境（Production；測試時也可選 Preview），儲存後觸發一次新的部署。
5. 部署完成後開啟 Vercel 提供的網址測試首頁、`/health`、音訊播放與下載。每次變更 Environment Variables 後都需重新部署才會套用。

## 外部音樂 API 整合說明

此 MVP 使用通用 HTTP JSON 契約，呼叫時以 `Authorization: Bearer <MUSIC_API_KEY>` 驗證，逾時上限為連線 5 秒、讀取 25 秒。請依所選服務的實際規格，在服務端配合提供上述端點及欄位；API 金鑰只在 Flask Function 讀取，不會傳到瀏覽器。生成任務 ID 應為該服務可透過狀態端點查詢的 ID。Vercel Function 不保存跨請求記憶體狀態，故任務狀態由外部音樂服務維護。

## 安全與部署備註

- `.env`、`.venv/`、`__pycache__/`、`.vercel/` 已列入 `.gitignore`；`.env.example` 僅提供空白變數名稱。
- 不使用常駐背景執行緒或本機持久儲存。大型音訊檔由外部服務提供 HTTPS URL。
- Python 執行環境支援與 Vercel 設定會隨平台更新，部署時請以 Vercel 最新官方文件為準。
