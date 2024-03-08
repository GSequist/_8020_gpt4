    hasLoadedPreviousConversations = false;    
    var responseInProgress = false;
    var hasClearedOutput = false;
    let cursorSpan = null;
    let iconFlag = false;
    let isAudioEnabled = false;
    let audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    
    ////////////////////////////////////////////////////websockets  


    //DOM load
    document.addEventListener('DOMContentLoaded', function () {
        console.log('DOMContentLoaded event triggered');
        getUserId();
    });

    //generating userID
    function generateUserId() {
    console.log('Generating new user ID');
    return uuid.v4();
    }

    //managing userid
    function getUserId() {
    let userId = localStorage.getItem('userId');

    if (userId === null) {
        userId = generateUserId();
        localStorage.setItem('userId', userId);
        console.log('New userID generated and set:', userId);
    } else {
        console.log('Existing userID found:', userId);
    }
    return userId;
    }

    const userId = getUserId();
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${location.host}/ws/${userId}`);

    socket.addEventListener('open', function (event) {
        console.log('Connected to server with user ID:', userId);
    });

    socket.addEventListener('error', function (event) {
        console.error('WebSocket error:', event);
    });

    socket.addEventListener('close', function (event) {
        console.log('Disconnected from the server. Refreshing page...');
        window.location.reload(); // enforce refresh
    });      

    ////////////////////////////////////////////////////modular formatting
    
    
    ////////////////////////////////////////////////elements
    //define elements
    const input = document.getElementById('input');
    const submit = document.getElementById('submit');
    const output = document.getElementById('output');
    const form = document.getElementById('text-form');
    const fileInput = document.getElementById('file');
    const typingButton = document.getElementById('typing');
    const uploadButton = document.getElementById('upload');
    const gifContainer = document.getElementById('process-gif-container');
    const toggleButton = document.querySelector('.toggleButton');
    const body = document.querySelector('body');
    const toggleTitle = document.querySelector('.toggleTitle');
    const logo = document.querySelector('.logo');
    const copyButton = document.querySelector('.copyButton');
    const voiceButton = document.querySelector('.voiceButton');
    const giantLogo = document.querySelector('.giant-logo');

    ////////////////////////////////////////////////////styling
    // toggle circle buttons logic
    body.style.backgroundColor = 'rgb(190, 190, 190)';

    toggleButton.addEventListener('click', function () {
        const isLightTheme = getComputedStyle(body).getPropertyValue('--background-color').trim() === 'rgb(190, 190, 190)';
        body.style.setProperty('--background-color', isLightTheme ? 'rgb(50, 50, 50)' : 'rgb(190, 190, 190)');

        if (body.style.backgroundColor === 'rgb(190, 190, 190)') {
        document.body.classList.toggle('darkmode');
        toggleButton.src = 'static/toggle_new_white.png';
        voiceButton.src = 'static/voice_white.png';
        body.style.backgroundColor = 'rgb(50, 50, 50)';
        giantLogo.src = 'static/logo_elements_large_white.png';
        toggleTitle.style.color = 'rgb(255, 255, 255)';
        toggleTitle.innerHTML = '_dark_is_beautiful_';
        logo.src = 'static/logo_elements_white.png';
        uploadButtonImage.src = 'static/upload_8020_white.png';
        submitButtonImage.src = 'static/send_8020_white.png';
        input.style.color = 'rgb(255, 255, 255)';
        input.style.borderBottom = '1px solid rgb(255, 255, 255)';
        output.style.color = 'rgb(255, 255, 255)';
        input.classList.remove('input-light-theme');
        input.classList.add('input-dark-theme');
        }
        else {
        toggleButton.src = 'static/toggle_new_black.png';
        voiceButton.src = 'static/voice.png';
        body.style.backgroundColor = 'rgb(190, 190, 190)';
        giantLogo.src = 'static/logo_elements_large_black.png';
        toggleTitle.style.color = 'rgb(0, 0, 0)';
        toggleTitle.innerHTML = '_8020_ai+_';
        logo.src = 'static/logo_elements_black.png';
        uploadButtonImage.src = 'static/upload_8020_black.png';
        submitButtonImage.src = 'static/send_8020_black.png';
        input.style.color = 'rgb(0, 0, 0)';
        input.style.borderBottom = '1px solid rgb(0, 0, 0)';
        output.style.color = 'rgb(0, 0, 0)';
        input.classList.remove('input-dark-theme');
        input.classList.add('input-light-theme');
        }
    });
    
    //submit & upload btn dynamic
    const submitButtonImage = submit.querySelector('img');
    const uploadButtonImage = uploadButton.querySelector('img');

    submit.addEventListener('mouseover', function () {
        submitButtonImage.src = body.style.backgroundColor === 'rgb(190, 190, 190)' 
            ? 'static/send_8020_pink.png' : 'static/send_8020_pink.png';
    });
    submit.addEventListener('mouseout', function () {
        submitButtonImage.src = body.style.backgroundColor === 'rgb(190, 190, 190)' 
            ? 'static/send_8020_black.png' : 'static/send_8020_white.png';
    });
    uploadButton.addEventListener('mouseover', function () {
        uploadButtonImage.src = body.style.backgroundColor === 'rgb(190, 190, 190)' 
            ? 'static/upload_8020_pink.png' : 'static/upload_8020_pink.png';
    });
    uploadButton.addEventListener('mouseout', function () {
        uploadButtonImage.src = body.style.backgroundColor === 'rgb(190, 190, 190)' 
            ? 'static/upload_8020_black.png' : 'static/upload_8020_white.png';
    });


    /////////////////////////////////////////////////////////////functional code
    //sending messages
    function sendMessage(event) {
        if (event) event.preventDefault();  
            if (responseInProgress) {
                return;
            }
            if (uploadInProgress) {
                return;
            }
            const message = input.value;
            if (!message) return;
            submit.disabled = true;
            const sourcesContainer = document.getElementById('sources-container');
            sourcesContainer.innerHTML = '';
            const fileContainer = document.querySelector('.file-container');
            if (fileContainer) {
                fileContainer.remove();
            }
            const copyButton = document.querySelector('.copyButton');
            if (copyButton) {
                copyButton.style.visibility = 'hidden';
            }
            input.value = '';
            
            const messageData = JSON.stringify({ message: message, user_id: getUserId() });
            console.log('sendMessage called:', messageData);
            socket.send(messageData); 
            console.log("WebSocket state after sending:", socket.readyState);
            }

            //submit with click
            submit.addEventListener('click', sendMessage);
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                sendMessage(event);
            });
            
            //submit with Enter
            input.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();  
                }
            });
    
    ////////////////////////////////////////////////listening to backend
    // helper for table rendering
    function createAndAppendTable(outputElement) {
        const table = document.createElement('table');
        outputElement.appendChild(table);
        return table;
    }

    function isTableFormat(data) {
        return data.includes('~');
    }

    let tableElement = null; 
    let isProcessingTable = false; 
    let currentRow = null; 
    let currentCell = null;
    
    // helper for code block rendering
    function createAndAppendCodeBlock(outputElement) {
        const codeBlock = document.createElement('pre');
        codeBlock.classList.add('code-block');
        outputElement.appendChild(codeBlock);
        return codeBlock;
    }

    let backtickSequence = '';
    let codeBlockElement = null;
    let isProcessingCode = false;

    function isCodeFormat(data) {
        backtickSequence += data;
        const tripleBacktickRegex = /(`\n*\n*`)\n*\n*`/;
        if (tripleBacktickRegex.test(backtickSequence)) {
            backtickSequence = ''; 
            return true;
        }
        if (backtickSequence.length > 100) { 
            backtickSequence = '';
        }
        return false;
    }


    // listen for response from server
    socket.addEventListener('message', function (event) {
            if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'response') {
            responseInProgress = true;
            stopTypewriter = true;
            if (!hasClearedOutput) {
                output.innerHTML = '';
                hasClearedOutput = true;
            }  
            document.getElementById('output').classList.remove('largeFont');
            if (!iconFlag) {
                document.getElementById('output').classList.remove('largeFont');
                iconSrc = body.style.backgroundColor === 'rgb(190, 190, 190)' 
                ? 'static/logo_elements_black.png' : 'static/logo_elements_white.png';
                const iconContainer = document.getElementById('icon-container');
                iconContainer.innerHTML = iconSrc ? `<img src="${iconSrc}" alt="" style="height: 20px;"/>` : '';
                output.appendChild(iconContainer);
                iconFlag = true;
            }  
            if (data.error) {
                console.log('Error received.');
                output.innerHTML += `<span class="error">${data.error}</span>`;
            } else {
            if (data.data.includes('±')) {
                isProcessingTable = false;
                tableElement = null; 
                currentRow = null; 
                currentCell = null;
                data.data = data.data.replace('±', '');
            }

            if (!isProcessingTable && isTableFormat(data.data)) {
                isProcessingTable = true;
                tableElement = createAndAppendTable(output);
                currentRow = document.createElement('tr');
                tableElement.appendChild(currentRow);
            }

            if (isProcessingTable) {
                let parts = data.data.split('~');
                parts.forEach((part, index) => {
                    let cells = part.split('|');
                    cells.forEach((cell, cellIndex) => {
                        if (cell) {
                            if (!currentCell) {
                                currentCell = document.createElement('td');
                                currentRow.appendChild(currentCell);
                            }
                            currentCell.textContent += cell;
                        }

                        if (cellIndex !== cells.length - 1) {
                            currentCell = document.createElement('td');
                            currentRow.appendChild(currentCell);
                        }
                    });

                    if (index !== parts.length - 1) {
                        currentRow = document.createElement('tr');
                        tableElement.appendChild(currentRow);
                        currentCell = null;
                    }
                });
                } else {
                if (isCodeFormat(data.data)) {
                    if (!isProcessingCode) {
                        isProcessingCode = true;
                        codeBlockElement = createAndAppendCodeBlock(output);
                    } else {
                        isProcessingCode = false;
                    }
                    data.data = data.data.replace('```', '');
                }

                if (isProcessingCode) {
                    let formattedCode = data.data;
                    if (formattedCode.includes('\n')) {
                        formattedCode = formattedCode.replace(/\n/g, '<br>');
                    }
                    codeBlockElement.innerHTML += `<span>${formattedCode}</span>`;
                    if (!isProcessingCode) {
                        codeBlockElement = null;
                    }
            } else {
                let messageContent = data.data;
                if (messageContent.includes('\n')) {
                    messageContent = messageContent.replace(/\n/g, '<br>');
                }
                if (!cursorSpan) {
                    cursorSpan = document.createElement('span');
                    cursorSpan.id = 'typing-cursor';
                    cursorSpan.classList.add('typing-cursor');
                }
                output.appendChild(cursorSpan);
                cursorSpan.insertAdjacentHTML('beforebegin', `<span>${messageContent}</span>`);
            }
        }
        }
    }
    });


    document.querySelector('.voiceButton').addEventListener('click', async function() {
        console.log('voiceButton clicked');
        isAudioEnabled = !isAudioEnabled; 
        socket.send(JSON.stringify({ type: "toggle_audio", isAudioEnabled: isAudioEnabled }));
        if (isAudioEnabled) {
            console.log("Audio playback enabled. Waiting for audio data...");
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
        } else {
            console.log("Audio playback disabled.");
            if (audioContext.state === 'running') {
                audioContext.suspend();
            }
        }
        });

    socket.addEventListener('message', function (event) {
    if (!isAudioEnabled) {
        console.log("Audio playback is disabled. Ignoring incoming audio data.");
        return; 
    }
    if (event.data instanceof Blob) {
        processAndPlayAudioBlob(event.data);
        console.log("Audio chunk loaded, process and play it here.");
    }
    });

    function processAndPlayAudioBlob(audioBlob) {
        const reader = new FileReader();
        reader.onload = function() {
            const arrayBuffer = reader.result;
            console.log("ArrayBuffer size:", arrayBuffer.byteLength);
            console.log("Data type:", typeof arrayBuffer);
                console.log("Data instance:", arrayBuffer instanceof ArrayBuffer);
                console.log("Data length:", arrayBuffer.byteLength);
            decodeAndPlay(arrayBuffer);
            }
            reader.readAsArrayBuffer(audioBlob);
        };

    function decodeAndPlay(arrayBuffer) {
        audioContext.decodeAudioData(arrayBuffer, function(decodedData) {
            const source = audioContext.createBufferSource();
            source.buffer = decodedData;
            source.connect(audioContext.destination);
            source.start(); 
            console.log("Audio should be playing now.");
        }, function(e) {
            console.error("Error with decoding audio data:", e);
        });
    }

    //helper for images rendering
    socket.addEventListener('message', function (event) {
        if (event.data instanceof Blob) {
            // Ignore binary data and continue listening
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'response' && data.payload && data.payload.img_url) {
            output.appendChild(document.createElement('br'));
            const imgElement = document.createElement('img');
            imgElement.src = data.payload.img_url; 
            output.appendChild(imgElement);
            output.appendChild(document.createElement('br'));
            
            output.scrollTop = output.scrollHeight;
        }
    });

    // helper download fetch 
    function fetchFilesForUser() {
        fetch(`/files/${getUserId()}`)
            .then((response) => response.json())
            .then((files) => {
                // check if there are files 
                if (files.length > 0) {
                    var message = document.createElement('p');
                    message.textContent = ">your files:";
                    output.appendChild(message);
                }
                // loop through the file list and create download links
                files.forEach(file => {
                    var fileContainer = document.createElement('div');
                    fileContainer.classList.add('file-container');

                    var link = document.createElement('a');
                    // link.href = `/download/${getUserId()}?file=${file}`;
                    link.href = `/download/${getUserId()}?file=${encodeURI(file)}`;
                    link.textContent = file;
                    link.target = '_blank';
                    link.classList.add('download-btn');
                    fileContainer.appendChild(link);

                    var deleteIcon = document.createElement('img');
                    deleteIcon.src = 'static/delete_8020_color.png'; 
                    deleteIcon.classList.add('delete-icon');
                    deleteIcon.onclick = function() {
                        deleteFile(file, link, deleteIcon);
                    };
                    fileContainer.appendChild(deleteIcon);
                    output.appendChild(fileContainer);
                });
                var br = document.createElement('br');
                output.appendChild(br);
                output.scrollTop = output.scrollHeight;
            });
    }

    // delete helper
    function deleteFile(fileName, linkElement, deleteIconElement) {
        fetch(`/delete/${getUserId()}/${fileName}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('File deleted:', fileName);
                    linkElement.style.color = 'grey';
                    linkElement.style.pointerEvents = 'none';
                    linkElement.style.textDecoration = 'line-through';
                    deleteIconElement.style.display = 'none';
                    linkElement.onmouseover = null;
                    linkElement.onmouseout = null;
                } else {
                    console.error('Failed to delete file:', fileName);
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // listen for new user message
    socket.addEventListener('message', function (event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'new_user_message') {
            stopTypewriter = true;
            if (!hasClearedOutput) {
                output.innerHTML = ''; 
                hasClearedOutput = true;
            }  
            document.getElementById('output').classList.remove('largeFont');
            const formattedMessage = data.data.replace(/\n/g, '<br>');
            output.innerHTML += `<span class="userMessage">${formattedMessage}</span><br><br>`;
        }
        output.scrollTop = output.scrollHeight;
    });

    // listen for 'previous_conversations' event
    socket.addEventListener('message', function (event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'previous_conversations') {
            if (!hasLoadedPreviousConversations) {
                stopTypewriter = true;
                if (!hasClearedOutput) {
                    output.innerHTML = ''; 
                    hasClearedOutput = true;
                    }  
                document.getElementById('output').classList.remove('largeFont');
                console.log('Previous conversations:', data.data);
                data.data.forEach(message => {
                    if (message.role === 'user') {
                        output.innerHTML += `<span class="userMessage">${message.content}</span><br><br>`;
                    } else {
                        const iconSrc = body.style.backgroundColor === 'rgb(190, 190, 190)' 
                        ? 'static/logo_elements_black.png' : 'static/logo_elements_white.png';
                        if (message.content.includes('\n')) {
                            message.content = message.content.replace(/\n/g, '<br>');
                        }
                        output.innerHTML += `<img src="${iconSrc}" alt="" style="height: 20px; border-radius: 50%; vertical-align: middle; margin-right: 5px;">` + `<span>${message.content}</span><br><br>`;
                        var hr = document.createElement('hr');
                        hr.style.borderTop = '0.5px dashed grey';
                        hr.style.borderBottom = 'none';
                        output.appendChild(hr);
                    }
                });
                hasLoadedPreviousConversations = true;
            }
            output.scrollTop = output.scrollHeight;
        }
    });

    //listen to signalling messages
    socket.addEventListener('message', function (event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'message') {
            const isWhiteBackground = document.body.style.backgroundColor === 'rgb(190, 190, 190)';

            let gifSrc = '';
            if (data.data.includes('web')) {
                gifSrc = isWhiteBackground ? 'static/gif_web.gif' : 'static/gif_web_white.gif';
            } else if (data.data.includes('vectorstore')) {
                gifSrc = isWhiteBackground ? 'static/gif_vector.gif' : 'static/gif_vector_white.gif'; 
            } else if (data.data.includes('thinking')) {
                gifSrc = isWhiteBackground ? 'static/gif_thinking.gif' : 'static/gif_thinking_white.gif'; 
            } else if (data.data.includes('image')) {
                gifSrc = isWhiteBackground ? 'static/gif_paint_black.gif' : 'static/gif_paint_white.gif'; 
            } else if (data.data.includes('brainstorming')) {
                gifSrc = isWhiteBackground ? 'static/gif_brainstorming_black.gif' : 'static/gif_brainstorming_white.gif'; 
            } else if (data.data.includes('deck')) {
                gifSrc = isWhiteBackground ? 'static/pptx_black.gif' : 'static/pptx_white.gif'; 
            }

            const gifContainer = document.getElementById('process-gif-container');
            gifContainer.innerHTML = gifSrc ? `<img src="${gifSrc}" alt="processing gif" style="height: 25px;" /><br>` : '';
            output.appendChild(gifContainer);
            output.scrollTop = output.scrollHeight;
        }
    });

    // listen for 'sources' event
    socket.addEventListener('message', function(event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'sources') {
            const sources = data.sources.combined;
            const uniqueSources = new Set(sources);
            displaySources(uniqueSources);
        }
    });
    function displaySources(sources) {
        const sourcesContainer = document.getElementById('sources-container');
        output.appendChild(sourcesContainer);
        sourcesContainer.innerHTML = '';
        sources.forEach(source => {
            const sourceElement = document.createElement('div');
            sourceElement.classList.add('source-item');
            sourceElement.textContent = source;
            sourcesContainer.appendChild(sourceElement);
        });
    }

    //listen for sources url
    socket.addEventListener('message', function(event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);
        if (data.type === 'sources_url') {
            const sourceUrl = data.sources_url;
            displaySource(sourceUrl);
        }
    });
    function displaySource(sourceUrl) {
        const sourcesContainer = document.getElementById('sources-container');
        if (sourceUrl) {
            const sourceElement = document.createElement('div');
            sourceElement.classList.add('source-item');
            const link = document.createElement('a');
            link.setAttribute('href', sourceUrl);
            link.setAttribute('target', '_blank'); 
            link.textContent = sourceUrl;
            sourceElement.appendChild(link);
            sourcesContainer.appendChild(sourceElement);
        }
    }

    //listen for proofreading
    socket.addEventListener('message', function(event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);
        if (data.type === 'proofreading') {
        const proofreadDoc = data.data; 
        console.log('Proofreading data:', proofreadDoc);
        const formattedContent = proofreadDoc.replace(/\n/g, '<br>'); 
        output.innerHTML += `<br><span>${formattedContent}</span><br>`;
        }
    });


    
    // listen for the end of messages
    socket.addEventListener('message', function (event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'endOfMessage') {
            submit.disabled = false;
            iconFlag = false;

            const gifContainer = document.getElementById('process-gif-container');
            gifContainer.innerHTML = ''; //clean 
            if (cursorSpan) {
                cursorSpan.remove();
                cursorSpan = null; // clean
            }
            const fileDisplayContainer = document.getElementById('file-display-container'); // Assuming this is your container
            if (fileDisplayContainer) {
                fileDisplayContainer.innerHTML = ''; // clear old files
            }
            fetchFilesForUser();

            var br = document.createElement('br');
            output.appendChild(br);

            var hr = document.createElement('hr');
            hr.style.borderTop = '0.5px dashed grey';
            hr.style.borderBottom = 'none';
            output.appendChild(hr);

            output.scrollTop = output.scrollHeight;

            responseInProgress = false;
            console.log("answer was fully emitted end of message");
            const copyButton = document.querySelector('.copyButton');
            if (copyButton) {
                copyButton.style.visibility = 'visible';
                output.appendChild(copyButton);
            }
            if (copyButton) {
                copyButton.addEventListener('click', async function() {
                    socket.send(JSON.stringify({ type: 'request_last_assistant_message' }));
                });
            }
        }
    });

    // copy button logic listener
    socket.addEventListener('message', function (event) {
        if (event.data instanceof Blob) {
            return;
        }
        const data = JSON.parse(event.data);

        if (data.type === 'last_assistant_message') {
            const textToCopy = data.data.content;
            navigator.clipboard.writeText(textToCopy).then(function() {
                console.log('Last assistant message text copied to clipboard');
            })
            .catch(function(error) {
                console.error('Could not copy text: ', error);
            });
        }
    });

    //////////////////////////////////////////////////uploading files

    // triggers file input when upload button is clicked
    uploadButton.addEventListener('click', function () {
    console.log('uploadButton clicked');
    if (!uploadInProgress) {
        fileInput.click();
    } else {
        input.value = '>upload in progress. Please wait...';
    }
    });

    // fileInput event listener
    fileInput.addEventListener('change', function (event) {
        console.log('fileInput change event');
        if (fileInput.files.length > 0) {
            checkFileSizeAndUpload(event);
        }
    });

    let uploadInProgress = false;

    // checks file size and initiates upload
    function checkFileSizeAndUpload(event) {
    console.log('checking file size');
    const maxFileSizeMB = 100;
    const files = event.target.files;

    // check if multiple files are selected
    if (files.length > 1) {
        input.value = '>please select only one file.';
        return;
    }

    const file = files[0];
    if (file.size > maxFileSizeMB * 1024 * 1024) {
        input.value = `>file size exceeds ${maxFileSizeMB} MB.`;
    } else {
        console.log('file size ok progressing to upload');
        uploadFile(file);
    }
    }

    // alternative upload files via fetch
    function uploadFile(file) {
        console.log('uploadFile called');
        uploadInProgress = true;
        input.value = `>uploading ${file.name}...`;
        uploadButton.classList.add('disabled-button');

        const formData = new FormData();
        formData.append('file', file);

        fetch(`/upload/${getUserId()}`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log('Upload response:', data);
            uploadInProgress = false;
            uploadButton.classList.remove('disabled-button');

            if (data.status === 'success') {
                input.value = `>file ${file.name} uploaded successfully`;
                aiInput = true; 
            } else if (data.status === 'error' && data.message === '>file size exceeded')
            {
                input.value = '>file size exceeded';
                aiInput = true;
            }
            else {
                input.value = `>error during upload of ${file.name}, sorry.`;
                aiInput = true;
            }
            input.addEventListener('focus', function() {
                if (aiInput) {
                    input.value = '';
                    aiInput = false;
                }
            });
        })
        .catch(error => {
            console.error('Error during file upload:', error);
            input.value = '>error during file upload.';
            uploadInProgress = false;
            uploadButton.classList.remove('disabled-button');
        });
    }


        //////////////////////////////////////////////////
        //typewriter effect
        function typeWriter(text, i, id) {
        const outputField = document.getElementById('output');
        outputField.classList.add('largeFont');

        if (stopTypewriter) {
            outputField.classList.remove('largeFont');
            return;
        }

        if (i < text.length) {
            outputField.innerHTML += text.charAt(i);
            i++;
            setTimeout(function () {
            typeWriter(text, i, id);
            }, 30);
        } else {
            setTimeout(function () {
            if (!stopTypewriter) {
                outputField.innerHTML = '';
                const messages = [
                'hello, welcome',
                'ask away',
                'I am here to help',
                ];
                const index = messages.indexOf(text);
                text = messages[(index + 1) % messages.length];
                typeWriter(text, 0, id);
            }
            }, 4000);
        }
        }

        var stopTypewriter = false;
        var text = 'hello welcome, ask away';
        typeWriter(text, 0, 'output');