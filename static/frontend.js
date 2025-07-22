let mediaRecorder, audioChunks = [];

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = sendAudioToBackend;
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

async function getGPTResponse(prompt) {
  const response = await fetch('/stream-gpt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const outputDiv = document.getElementById("gpt-output");
  outputDiv.textContent = "";  // Clear old content

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    outputDiv.textContent += chunk;
  }
}
