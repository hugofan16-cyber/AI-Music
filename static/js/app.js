const form = document.querySelector("#music-form");
const promptField = document.querySelector("#prompt");
const count = document.querySelector("#char-count");
const generateButton = document.querySelector(".generate");
const notice = document.querySelector("#notice");
const result = document.querySelector("#result");
const audio = document.querySelector("#audio-player");
const download = document.querySelector("#download-link");
const summary = document.querySelector("#summary");
const demoNote = document.querySelector("#demo-note");

const genreNames = { lofi: "Lo-Fi", pop: "流行 Pop", rock: "搖滾 Rock", electronic: "電子", cinematic: "電影配樂", hiphop: "嘻哈", acoustic: "原聲" };
const moodNames = { relaxing: "放鬆", energetic: "熱血", dreamy: "夢幻", hopeful: "希望", dark: "暗黑", focus: "專注" };

promptField.addEventListener("input", () => { count.textContent = `${promptField.value.length} / 500`; });
document.querySelectorAll(".idea").forEach((button) => button.addEventListener("click", () => {
  promptField.value = button.dataset.prompt;
  count.textContent = `${promptField.value.length} / 500`;
  promptField.focus();
}));

function showError(message) {
  notice.textContent = message || "發生未預期的問題，請稍後再試。";
  notice.hidden = false;
}

function showTrack(data, settings) {
  audio.src = data.audio_url;
  download.href = data.download_url || data.audio_url;
  summary.textContent = `${genreNames[settings.genre]} · ${moodNames[settings.mood]} · ${settings.duration === "120" ? "2 分鐘" : `${settings.duration} 秒`} · ${settings.prompt}`;
  demoNote.hidden = data.mode !== "demo";
  result.hidden = false;
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function readResponse(response) {
  let data;
  try { data = await response.json(); }
  catch { throw new Error("伺服器回傳格式異常，請稍後再試。"); }
  if (!response.ok || data.ok === false) throw new Error(data.error?.message || "目前無法生成音樂，請稍後再試。");
  return data;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (generateButton.disabled) return;
  const settings = {
    prompt: promptField.value.trim(),
    genre: document.querySelector("#genre").value,
    mood: document.querySelector("#mood").value,
    duration: document.querySelector("#duration").value,
  };
  if (!settings.prompt) { showError("先寫下一段音樂靈感再開始生成。"); promptField.focus(); return; }
  notice.hidden = true;
  result.hidden = true;
  generateButton.disabled = true;
  generateButton.classList.add("loading");
  generateButton.querySelector(".button-copy").textContent = "生成中...";
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    let data = await readResponse(response);
    if (data.status === "queued" || data.status === "processing") {
      if (!data.task_id) throw new Error("音樂任務尚未回傳編號，請稍後再試。");
      let attempts = 0;
      while (attempts < 40) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        const statusResponse = await fetch(`/api/status/${encodeURIComponent(data.task_id)}`);
        data = await readResponse(statusResponse);
        if (data.status === "failed") throw new Error("這次生成沒有成功，換個靈感再試一次吧。");
        if (data.status === "succeeded" && data.audio_url) break;
        attempts += 1;
      }
      if (data.status !== "succeeded" || !data.audio_url) throw new Error("生成時間比預期久，請稍後查看或重新試一次。");
    }
    if (!data.audio_url) throw new Error("音樂已生成，但目前沒有可播放的音訊連結。");
    showTrack(data, settings);
  } catch (error) {
    showError(error.message);
  } finally {
    generateButton.disabled = false;
    generateButton.classList.remove("loading");
    generateButton.querySelector(".button-copy").textContent = "✦　生成我的音樂";
  }
});
