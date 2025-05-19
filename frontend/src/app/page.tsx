'use client';
import React, { useState, useRef, useEffect, Fragment } from 'react';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { useIsMobile } from './useIsMobile'; // Custom hook to check if the device is mobile

//import Image from "next/image";

// This is the home page of the application. This is React code with TypeScript enabled and Tailwind CSS.
// Tailwind CSS makes it easy to style the UI by using breakpoints to form a mobile-first, responsive layout with inline styles. 

type MessageContentBlock =
  | { type: 'text'; content: string }
  | { type: 'link'; url: string; label: string }
  | { type: 'attachment'; url: string; label: string }
  // Add more as needed

type Message = {
  sender: 'User' | 'Assistant';
  content: MessageContentBlock[];
};

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listeningMessage, setListeningMessage] = useState<string | null>(null);
  const [listeningCancelled, setListeningCancelled] = useState(false);
  const [lastMessageIsAudio, setLastMessageIsAudio] = useState(false);

  // Generate a unique user ID for each session.
  // This way, the backend will be able to handle multiple users at the same time.
  const [userId] = useState<string | null>(crypto.randomUUID());

  // Text input ref - used to focus on the input field
  const inputRef = useRef<HTMLInputElement>(null);
  // Message log ref - used to scroll the message log to the bottom when a new message is added.
  const messageLogRef = useRef<HTMLDivElement>(null);

  const handleSend = async (audio: boolean, textOverride?: string) => {

    // Prevent sending empty messages
    if (!textOverride && !message.trim()) return;
    
    setLastMessageIsAudio(audio);

    // Set message to the text override if provided. Otherwise, current message is used.
    if (textOverride) {
      setMessage(textOverride);
    }

    setLoading(true);
    setError(null);

    // Add user message to log
    const userMessage: Message = {
      sender: 'User',
      content: [{ type: 'text', content: message }],
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      const startTime = Date.now();

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, { // process.env.NEXT_PUBLIC makes the environment variable available in the browser (it is public)
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, userId, audio }),
      });

      const endTime = Date.now();
      console.log(`Backend request took ${((endTime - startTime) / 1000).toFixed(1)} seconds`);

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const data = await res.json();
      const assistantMessage: Message = {
        sender: 'Assistant',
        content: data.response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setMessage(''); // clear input after send
    } catch (err: unknown ) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred.');
      };
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend(false);
    }
  };

  const isMobile = useIsMobile();

  useEffect(() => {
    if (!isMobile && !loading && inputRef.current && !lastMessageIsAudio) {
      inputRef.current.focus(); // Focus on the input field after receiving a response, so the user can immediately type a new message
    }
    // Scroll message log to bottom when messages change
    if (messageLogRef.current) {
      messageLogRef.current.scrollTop = messageLogRef.current.scrollHeight;
    }
  }, [messages]);

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  // Debounce effect: Every time the transcript changes, set a timeout to stop listening after 2 seconds of silence. New transcript changes will reset the timeout.
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastTranscriptRef = useRef(transcript);
  useEffect(() => {
    if (!transcript) return;

    // Update the input field text with the current transcript and scroll to the right
    if (inputRef.current && !listeningCancelled) {
      setMessage(transcript);
      const input = inputRef.current;
      input.scrollLeft = input.scrollWidth;
    }

    // Clear previous timeout if it exists
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    // If transcript hasn’t changed in 2s, stop listening and send
    debounceTimeoutRef.current = setTimeout(() => {
      if (transcript === lastTranscriptRef.current) {
        SpeechRecognition.stopListening();
      }
    }, 2000); // 2-second silence buffer. If in two seconds any new words aren't added, the microphone will stop listening. 

    // Update last known transcript
    lastTranscriptRef.current = transcript;

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [transcript]);

  // When listening changes from true to false, it is sent.
  useEffect(() => {
    if (!listening && transcript && !listeningCancelled) {
      setListeningMessage(null);
      setMessage(transcript); // Set the message to the transcript
      handleSend(true);           // Send the message
      resetTranscript();      // Clear the transcript
    }
    else if (listening) {
      setListeningMessage('Wait...');
      setTimeout(() => {
        setListeningMessage('Listening...');
      }, 1000);
    }
    else {
      setListeningMessage(null);
    }
  }, [listening]);

  /* if (!browserSupportsSpeechRecognition) {
    return <span>Browser doesn't support speech recognition.</span>;
  } */

  const handleMicrophoneClick = () => {
    if (!listening) {
      resetTranscript();
      setListeningCancelled(false);
      SpeechRecognition.startListening({ continuous: true, language: 'en-US' }) // Finnish language: 'fi-FI' - it works! 
    } else {
      SpeechRecognition.stopListening();
      setListeningCancelled(true);
      setMessage(''); // Clear the message input when stopping listening
      resetTranscript();
    }
  }

  return (
    <div className="items-center justify-items-center min-h-screen p-8 py-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-6 row-start-2 items-center">
        <h1 className="text-2xl sm:text-4xl font-normal tracking-[-.01em] text-center text-Nordea-text-dark-blue">
          Hi Elina! <br /> How can I help you today?
        </h1>
        {messages.length == 0 ? <p className="text-md text-center font-normal text-Nordea-dark-grey">
          I am Nia, your personal <br/> <span className='font-bold'>financial</span> and <span className='font-bold'>banking</span> AI-assistant <br/> here at Nordea.
        </p> : null}
        <div className="flex flex-col gap-2 w-full items-center">
          {/* Message log */}
          <div
            className="flex flex-col gap-2 max-md:w-full md:w-96 max-h-96 overflow-y-scroll"
            ref={messageLogRef}
            style={{
              scrollbarWidth: messages.length > 5 ? 'auto' : 'none', // Chrome, Firefox, Safari, Edge
              msOverflowStyle: messages.length > 5 ? 'auto' : 'none',
            }}
          >
            {messages.map((msg, idx) => (
              <Fragment key={idx + 'Msg'}>
                <div
                  className={`py-3 px-4 rounded-t-3xl whitespace-pre-wrap ${
                    msg.sender === 'User'
                      ? 'bg-Nordea-text-dark-blue text-white self-end rounded-l-3xl ml-3'
                      : 'bg-Nordea-light-blue-1 text-Nordea-text-dark-blue self-start rounded-r-3xl mr-3'
                  }`}
                >
                  {msg.content.map((item, i) => {
                    switch (item.type) {
                      case 'text':
                        return <span key={i}>{item.content}</span>; 
                      case 'link':
                        return (
                          <span key={i} className="gap-1 bg-white rounded-xl px-2 mx-1">
                            {/*<svg className="fill-Nordea-accent-2" xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="24px"><path d="M480-80q-82 0-155-31.5t-127.5-86Q143-252 111.5-325T80-480q0-83 31.5-155.5t86-127Q252-817 325-848.5T480-880q83 0 155.5 31.5t127 86q54.5 54.5 86 127T880-480q0 82-31.5 155t-86 127.5q-54.5 54.5-127 86T480-80Zm0-82q26-36 45-75t31-83H404q12 44 31 83t45 75Zm-104-16q-18-33-31.5-68.5T322-320H204q29 50 72.5 87t99.5 55Zm208 0q56-18 99.5-55t72.5-87H638q-9 38-22.5 73.5T584-178ZM170-400h136q-3-20-4.5-39.5T300-480q0-21 1.5-40.5T306-560H170q-5 20-7.5 39.5T160-480q0 21 2.5 40.5T170-400Zm216 0h188q3-20 4.5-39.5T580-480q0-21-1.5-40.5T574-560H386q-3 20-4.5 39.5T380-480q0 21 1.5 40.5T386-400Zm268 0h136q5-20 7.5-39.5T800-480q0-21-2.5-40.5T790-560H654q3 20 4.5 39.5T660-480q0 21-1.5 40.5T654-400Zm-16-240h118q-29-50-72.5-87T584-782q18 33 31.5 68.5T638-640Zm-234 0h152q-12-44-31-83t-45-75q-26 36-45 75t-31 83Zm-200 0h118q9-38 22.5-73.5T376-782q-56 18-99.5 55T204-640Z"/></svg>
                         */}<a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-Nordea-accent-2 underline text-sm"
                            >
                              {item.label}
                            </a>
                          </span>
                        );
                      case 'attachment':
                        return (
                          <div key={i} className='my-4'>
                            <a className="border px-4 p-2 rounded-3xl bg-white shadow-sm" href={item.url} target="_blank" rel="noopener noreferrer">{`📎 ${item.label}`}</a>
                          </div>
                        );
                      default:
                        return null;
                    }
                  })}
                </div>
                {msg.sender === 'Assistant' ? (
                  <p className="text-Nordea-text-dark-blue text-sm -mt-2">Nia</p>
                ) : null}
              </Fragment>
            ))}
          </div>

          {error && <p className="text-red-600">Error: {error}</p>}
          <div className='flex flex-row gap-2 pt-6 max-w-full'>
            <div className='flex'>
            <input
              type="text"
              ref={inputRef} // Focus on text input when response is received
              placeholder="Ask a question..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              className="bg-Nordea-light-grey pl-4 lg:w-80 pr-14 rounded-full text-Nordea-text-dark-blue disabled:opacity-50"
            />
            <button
              onClick={() => handleSend(false, message)}
              disabled={loading}
              className="bg-transparent text-white rounded-full -ml-11 hover:bg-Nordea-light-blue-2 disabled:opacity-50 cursor-pointer"
            >
              {/* {loading ? 'Send' : 'Send'} {/* {loading ? 'Sending...' : 'Send'} */} 
              <svg className="fill-Nordea-text-dark-blue w-11 p-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M12.627 8.75H0.5V7.25H12.627L6.93075 1.55375L8 0.5L15.5 8L8 15.5L6.93075 14.4462L12.627 8.75Z"/></svg>
            </button>
            </div>
              <button 
              className={`rounded-full md:hover:bg-Nordea-accent-blue cursor-pointer ${
                listening ? 'bg-Nordea-green' : 'bg-Nordea-text-dark-blue'
              }`}
              onClick={() => handleMicrophoneClick()}
              >
              <svg className="fill-white w-11 p-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44"><path d="M22 24.6999C20.7424 24.6999 19.678 24.2643 18.8068 23.3931C17.9356 22.5219 17.5 21.4575 17.5 20.1999V9.3999C17.5 8.1423 17.9356 7.0779 18.8068 6.2067C19.678 5.3355 20.7424 4.8999 22 4.8999C23.2576 4.8999 24.322 5.3355 25.1932 6.2067C26.0644 7.0779 26.5 8.1423 26.5 9.3999V20.1999C26.5 21.4575 26.0644 22.5219 25.1932 23.3931C24.322 24.2643 23.2576 24.6999 22 24.6999ZM20.65 37.7499V31.8167C17.68 31.4774 15.2125 30.2036 13.2475 27.9953C11.2825 25.7866 10.3 23.1882 10.3 20.1999H13C13 22.6899 13.8775 24.8124 15.6325 26.5674C17.3875 28.3224 19.51 29.1999 22 29.1999C24.49 29.1999 26.6125 28.3224 28.3675 26.5674C30.1225 24.8124 31 22.6899 31 20.1999H33.7C33.7 23.1882 32.7175 25.7866 30.7525 27.9953C28.7875 30.2036 26.32 31.4774 23.35 31.8167V37.7499H20.65Z"/></svg>
              </button>
          </div>
          <p className='text-Nordea-text-dark-blue opacity-70 text-sm'>{listeningCancelled ? null : listeningMessage}</p> {/* Show whether microphone is ready*/} 
        </div>
      </main>
    </div>
  );
}
