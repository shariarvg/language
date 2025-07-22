let mediaRecorder, audioChunks = [];

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = handleUserAudio;
  audioChunks = [];
  mediaRecorder.start();
}

function stopRecording() {
  mediaRecorder.stop();
}

async function sendAudioToBackend() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');

  const response = await fetch('/backend/upload-audio', {
    method: 'POST',
    body: formData
  });

  const reader = response.body.getReader();
  const audioContext = new AudioContext();
  let sourceBuffer = audioContext.createBufferSource();
  const stream = new ReadableStream({
    async start(controller) {
      while (true) {
        const { done, value } = await reader.read();
        
        // decode and play streamed audio
        const audioBuffer = await audioContext.decodeAudioData(value.buffer);
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();
        if (done) break;
      }
      controller.close();
    }
  });
  
}

async function getGPTResponse() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');

  const response = await fetch('/backend/stream-gpt', {
    method: 'POST',
    body: formData
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const outputDiv = document.getElementById("gpt-output");
  outputDiv.innerText = "";  // Clear previous response

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    outputDiv.innerText += decoder.decode(value, { stream: true });
  }
}

async function handleUserAudio() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append("file", audioBlob, "audio.webm");

  // Step 1: Transcribe user audio
  const transcriptResponse = await fetch('/backend/transcribe-audio', {
    method: 'POST',
    body: formData
  });

  const { text: userText } = await transcriptResponse.json();

  // Step 2: Add user message to chat
  const chatContainer = document.getElementById("chat-container");

  const userMsgDiv = document.createElement("div");
  userMsgDiv.className = "user-msg";
  userMsgDiv.innerText = userText;
  chatContainer.appendChild(userMsgDiv);

  // Step 3: Create GPT placeholder message
  const gptMsgDiv = document.createElement("div");
  gptMsgDiv.className = "gpt-msg";
  chatContainer.appendChild(gptMsgDiv);

  // Step 4: Stream GPT response
  const gptResponse = await fetch('/backend/continue-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: userText })
  });

  const reader = gptResponse.body.getReader();
  const decoder = new TextDecoder("utf-8");

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    gptMsgDiv.innerText += decoder.decode(value, { stream: true });
    chatContainer.scrollTop = chatContainer.scrollHeight;  // auto-scroll
  }
}


