    hasLoadedPreviousConversations = false;    
    var responseInProgress = false;
    var hasClearedOutput = false;
    let cursorSpan = null;

    ////////////////////////////////////////////////////websockets  

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
    const socket = new WebSocket(`wss://${location.host}/ws/${userId}`);

    socket.addEventListener('open', function (event) {
        console.log('Connected to server with user ID:', userId);
    });

    socket.addEventListener('error', function (event) {
        console.error('WebSocket error:', event);
    });

    socket.addEventListener('close', function (event) {
        console.log('Disconnected from the server.');
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
    const messages = document.getElementById('messages');
    const gifContainer = document.getElementById('process-gif-container');
    const toggleButton = document.querySelector('.toggleButton');
    const body = document.querySelector('body');
    const giantText = document.querySelector('.giant-text');
    const toggleTitle = document.querySelector('.toggleTitle');
    const logo = document.querySelector('.logo');

    ////////////////////////////////////////////////////styling
    // toggle circle buttons logic
    body.style.backgroundColor = 'rgb(255, 255, 255)';

    toggleButton.addEventListener('click', function () {
        const isLightTheme = getComputedStyle(body).getPropertyValue('--background-color').trim() === 'rgb(255, 255, 255)';
        body.style.setProperty('--background-color', isLightTheme ? 'rgb(50, 50, 50)' : 'rgb(255, 255, 255)');

        if (body.style.backgroundColor === 'rgb(255, 255, 255)') {
        document.body.classList.toggle('darkmode');
        toggleButton.src = 'static/toggle_white.png';
        body.style.backgroundColor = 'rgb(50, 50, 50)';
        giantText.style.color = 'rgb(255, 255, 255)';
        toggleTitle.style.color = 'rgb(255, 255, 255)';
        toggleTitle.innerHTML = '_dark_is_beautiful';
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
        toggleButton.src = 'static/toggle_black.png';
        body.style.backgroundColor = 'rgb(255, 255, 255)';
        giantText.style.color = 'rgb(0, 0, 0)';
        toggleTitle.style.color = 'rgb(0, 0, 0)';
        toggleTitle.innerHTML = '_8020_gpt4_';
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
    
    //pointer light beam logic
    document.addEventListener('DOMContentLoaded', function () {
    const cursorLight = document.createElement('div');
    cursorLight.id = 'cursor-light';
    document.body.appendChild(cursorLight);
    const toggleButton = document.querySelector('.toggleButton');

    document.addEventListener('mousemove', function (e) {
        cursorLight.style.left = e.pageX + 'px';
        cursorLight.style.top = e.pageY + 'px';

        // check if cursor is near ToggleButton
        const rect = toggleButton.getBoundingClientRect();
        const distanceX = Math.abs(e.pageX - (rect.left + rect.right) / 2);
        const distanceY = Math.abs(e.pageY - (rect.top + rect.bottom) / 2);
        const maxDistance = 80; 

        if (distanceX <= maxDistance && distanceY <= maxDistance) {
        cursorLight.style.background =
            'radial-gradient(circle, yellow 80%, transparent 20%)';
        cursorLight.style.width = '60px';
        cursorLight.style.height = '60px';
        } else {
        cursorLight.style.background =
            'radial-gradient(circle, yellow 30%, transparent 90%)';
        cursorLight.style.width = '40px';
        cursorLight.style.height = '40px';
        }
    });
    });

    //submit & upload btn dynamic
    const submitButtonImage = submit.querySelector('img');
    const uploadButtonImage = uploadButton.querySelector('img');

    submit.addEventListener('mouseover', function () {
        submitButtonImage.src = body.style.backgroundColor === 'rgb(255, 255, 255)' 
            ? 'static/send_8020_pink.png' : 'static/send_8020_pink.png';
    });
    submit.addEventListener('mouseout', function () {
        submitButtonImage.src = body.style.backgroundColor === 'rgb(255, 255, 255)' 
            ? 'static/send_8020_black.png' : 'static/send_8020_white.png';
    });
    uploadButton.addEventListener('mouseover', function () {
        uploadButtonImage.src = body.style.backgroundColor === 'rgb(255, 255, 255)' 
            ? 'static/upload_8020_pink.png' : 'static/upload_8020_pink.png';
    });
    uploadButton.addEventListener('mouseout', function () {
        uploadButtonImage.src = body.style.backgroundColor === 'rgb(255, 255, 255)' 
            ? 'static/upload_8020_black.png' : 'static/upload_8020_white.png';
    });


    /////////////////////////////////////////////////////////////functional code
    //sending messages
    function sendMessage(event) {
    if (event) event.preventDefault();  
        if (responseInProgress) {
            messages.innerHTML = '>response in progress .. please wait..';
            return;
        }
        if (uploadInProgress) {
            messages.innerHTML = ">upload in progress .. please wait...";
            return;
        }
        const message = input.value;
        submit.disabled = true;
        input.value = '';
        if (!message) return;
            const messageData = JSON.stringify({ message: message, user_id: getUserId() });
            console.log('sendMessage called:', messageData);
            socket.send(messageData); 
            console.log("WebSocket state after sending:", socket.readyState);
            }

            submit.addEventListener('click', sendMessage);
            form.addEventListener('submit', sendMessage);

            input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            sendMessage(event);  
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
        return data.includes('^');
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

    function isCodeFormat(data) {
        return data.includes('~');
    }

    let codeBlockElement = null;
    let isProcessingCode = false;

    // listen for response from server
    socket.addEventListener('message', function (event) {
        const data = JSON.parse(event.data);

        if (data.type === 'response') {
            responseInProgress = true;
            stopTypewriter = true;
            if (!hasClearedOutput) {
                output.innerHTML = '';
                hasClearedOutput = true;
            }  
            document.getElementById('output').classList.remove('largeFont');
            
            if (!cursorSpan) {
                cursorSpan = document.createElement('span');
                cursorSpan.id = 'typing-cursor';
                cursorSpan.classList.add('typing-cursor');
                output.appendChild(cursorSpan);
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
                let parts = data.data.split('^');
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
                    // Toggle code processing state if backticks are found
                    if (!isProcessingCode) {
                        isProcessingCode = true;
                        codeBlockElement = createAndAppendCodeBlock(output);
                    } else {
                        isProcessingCode = false;
                    }
                    // Remove the backticks from the data
                    data.data = data.data.replace('~', '');
                }

                if (isProcessingCode) {
                    // Append text to the code block element
                    let formattedCode = data.data;
                    if (formattedCode.includes('\n')) {
                        formattedCode = formattedCode.replace(/\n/g, '<br>');
                    }
                    codeBlockElement.innerHTML += `<span>${formattedCode}</span>`;

                    // Check if the closing backticks are in the current data
                    if (!isProcessingCode) {
                        codeBlockElement = null;
                    }
            } else {
                let messageContent = data.data;
                if (messageContent.includes('\n')) {
                    messageContent = messageContent.replace(/\n/g, '<br>');
                }
                cursorSpan.insertAdjacentHTML('beforebegin', `<span>${messageContent}</span>`);
            }
        }
        output.scrollTop = output.scrollHeight;
        }
    }
    });


    //helper for images rendering
    socket.addEventListener('message', function (event) {
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
                    link.href = `/download/${getUserId()}?file=${file}`;
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
                    fetchFilesForUser();
                } else {
                    console.error('Failed to delete file:', fileName);
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // listen for 'new_user_message' event
    socket.addEventListener('message', function (event) {
        const data = JSON.parse(event.data);

        if (data.type === 'new_user_message') {
            stopTypewriter = true;
            if (!hasClearedOutput) {
                output.innerHTML = ''; 
                hasClearedOutput = true;
                }  
            document.getElementById('output').classList.remove('largeFont');
            output.innerHTML += `<span class="userMessage">${data.data}</span><br><br>`;
        }
        output.scrollTop = output.scrollHeight;
    });

    // listen for 'previous_conversations' event
    socket.addEventListener('message', function (event) {
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
                        if (message.content.includes('\n')) {
                            message.content = message.content.replace(/\n/g, '<br>');
                        }
                        output.innerHTML += `<span>${message.content}</span><br><br>`;
                    }
                });
                hasLoadedPreviousConversations = true;
            }
            output.scrollTop = output.scrollHeight;
        }
    });


    //listen to signalling messages
    socket.addEventListener('message', function (event) {
        const data = JSON.parse(event.data);

        if (data.type === 'message') {
            const isWhiteBackground = document.body.style.backgroundColor === 'rgb(255, 255, 255)';

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
                gifSrc = isWhiteBackground ? 'static/gif_pptx.gif' : 'static/gif_pptx.gif'; 
            }

            const gifContainer = document.getElementById('process-gif-container');
            gifContainer.innerHTML = gifSrc ? `<img src="${gifSrc}" alt="processing gif" style="height: 25px;" /><br>` : '';
            output.appendChild(gifContainer);
            output.scrollTop = output.scrollHeight;
        }
    });

    // listen for 'sources' event
    socket.addEventListener('message', function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'sources') {
            const sources = data.sources.combined;
            displaySources(sources);
        }
    });

    function displaySources(sources) {
        const sourcesContainer = document.getElementById('sources-container');
        var br = document.createElement('br');
        output.appendChild(br);
        output.appendChild(sourcesContainer);
        sourcesContainer.innerHTML = ''; 

        sources.forEach(source => {
            const sourceElement = document.createElement('div');
            sourceElement.classList.add('source-item');
            sourceElement.textContent = source;
            sourcesContainer.appendChild(sourceElement);
        });
    }


    // listen for the end of messages
    socket.addEventListener('message', function (event) {
        const data = JSON.parse(event.data);

        if (data.type === 'endOfMessage') {
            submit.disabled = false;

            const gifContainer = document.getElementById('process-gif-container');
            gifContainer.innerHTML = ''; //clean 
            input.value = ''; //clean
            if (cursorSpan) {
                cursorSpan.remove();
                cursorSpan = null; // clean
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
            console.log("answer was fully emitted end of message")
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
            } else if (data.status === 'error' && data.message === '>file size exceeded')
            {
                input.value = '>file size exceeded';
            }
            else {
                input.value = `>error during upload of ${file.name}, sorry.`;
            }
            input.addEventListener('focus', function() {
                input.value = '';
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
                'your documents compressed to a Q&A box',
                'they say i am IQ 140+',
                'tell me your idea and ask me to brainstorm on it..',
                'i can create presentation, try me..',
                'i have many ideas about how AI can be used for your clients, ask me..',
                'i am good at images too..',
                'google? aww that is so 2022, ask me instead',
                'i can do tables, you know..',
                'please remember if you leave the page open too long your browser forgets your id, your docs will be deleted and ill forget our conversation',
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