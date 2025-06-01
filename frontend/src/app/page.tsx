'use client';
import React, { useState, useRef, useEffect, Fragment } from 'react';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';

import { useIsMobile } from './useIsMobile'; // Custom hook to check if the device is mobile
import { useLanguage } from './context/LanguageContext'
import { translations } from './lib/translations'; // Import translations for different languages

//import Image from "next/image";

// This is the home page of the application. This is React code with TypeScript enabled and Tailwind CSS.
// Tailwind CSS makes it easy to style the UI by using breakpoints to form a mobile-first, responsive layout with inline styles. 

type MessageContentBlock =
  | { type: 'text'; content: string }
  | { type: 'link'; url: string; label: string }
  | { type: 'attachment'; url: string; label: string }
  | { type: 'audio'; content: string; format: string }; // <-- Add audio type

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

  const { language } = useLanguage();
  const t = translations[language as 'EN' | 'FI'];
  const languageLocaleMap = {
    EN: 'en-US',
    FI: 'fi-FI',
  };

  // Generate a unique user ID for each session.
  // This way, the backend will be able to handle multiple users at the same time.
  const [userId] = useState<string | null>(crypto.randomUUID());

  // Text input ref - used to focus on the input field
  const inputRef = useRef<HTMLInputElement>(null);
  // Message log ref - used to scroll the message log to the bottom when a new message is added.
  const messageLogRef = useRef<HTMLDivElement>(null);

  // Store audio URLs for playback to avoid re-creating object URLs
  const audioUrlCache = useRef<{ [base64: string]: string }>({});

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

    const langCode = languageLocaleMap[language as 'EN' | 'FI'];

    try {
      const startTime = Date.now();

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, { // process.env.NEXT_PUBLIC makes the environment variable available in the browser (it is public)
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, userId, audio, langCode }),
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

      // Play audio if present in the response
      const audioBlock = data.response.find(
        (item: MessageContentBlock) => item.type === 'audio'
      );
      if (audioBlock && audioBlock.type === 'audio') {
        let audioUrl = audioUrlCache.current[audioBlock.content];
        if (!audioUrl) {
          audioUrl = `data:audio/${audioBlock.format};base64,${audioBlock.content}`;
          audioUrlCache.current[audioBlock.content] = audioUrl;
        }
        const audioObj = new Audio(audioUrl);
        audioObj.play();
      }
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
    // Scroll the entire page to the bottom to ensure input and buttons are visible
    //window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
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
      setListeningMessage(t.micWait);
      setTimeout(() => {
        setListeningMessage(t.micSpeak);
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
      const locale = languageLocaleMap[language as 'EN' | 'FI'];
      resetTranscript();
      setListeningCancelled(false);
      SpeechRecognition.startListening({ continuous: true, language: locale })
    } else {
      SpeechRecognition.stopListening();
      setListeningCancelled(true);
      setMessage(''); // Clear the message input when stopping listening
      resetTranscript();
    }
  }

  // Helper to parse **bold** in text and render as <span className="font-bold">
  function renderWithBold(text: string) {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, idx) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return (
      <span key={idx} className="font-bold">
        {part.slice(2, -2)}
      </span>
      );
    }
    return <span key={idx}>{part}</span>;
    });
  }

  return (
    <div className="items-center justify-items-center min-h-screen p-8 py-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-6 row-start-2 items-center">
        <div className="text-2xl sm:text-4xl font-normal tracking-[-.01em] text-center text-Nordea-text-dark-blue">
          {messages.length === 0 && (
            <h1>{t.greeting.split('\n').map((line, i) => <span key={i}>{line}<br/></span>)}</h1> 
          )}
        </div>
        {messages.length === 0 && (
          <p className="text-md text-center font-normal text-Nordea-dark-grey">
            {t.intro.split('\n').map((line, i) =>
              <span key={i}>{line}<br/></span>
            )}
          </p>
        )}
        <div className="flex flex-col gap-2 w-full items-center">
          {/* Message log */}
          <div
            className="flex flex-col gap-2 max-md:w-full md:w-[600px] max-h-[450px] md:max-h-[500px] overflow-y-scroll"
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
                        return <span key={i}>{renderWithBold(item.content)} </span>;
                      case 'link':
                      // Check if the link is a PDF
                      const isPdf = item.url.toLowerCase().endsWith('.pdf');
                      return isPdf ? (
                        <div key={i} className='my-4'>
                          <a className="border px-4 p-2 rounded-3xl bg-white shadow-sm" href={item.url} target="_blank" rel="noopener noreferrer">{`📎 ${item.label}`}</a>
                        </div>
                      ) : (
                        <Fragment key={idx + 'link'}>
                          <br/>
                          <span key={i} className="gap-1 bg-white rounded-xl px-2 mx-1">
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-Nordea-accent-2 underline text-sm"
                            >
                              {item.label}
                            </a>
                          </span>
                        </Fragment>
                      );
                    case 'attachment':
                      return (
                        <div key={i} className='my-4'>
                          <a className="border px-4 p-2 rounded-3xl bg-white shadow-sm" href={item.url} target="_blank" rel="noopener noreferrer">{`📎 ${item.label}`}</a>
                        </div>
                      );
                    /* case 'audio':
                      // Render audio player for audio responses
                      const audioUrl =
                        audioUrlCache.current[item.content] ||
                        `data:audio/${item.format};base64,${item.content}`;
                      audioUrlCache.current[item.content] = audioUrl;
                      return (
                        <audio
                          key={i}
                          controls
                          src={audioUrl}
                          className="my-2"
                        >
                          Your browser does not support the audio element.
                        </audio>
                      ); */
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
            {loading ? <div className="text-Nordea-dark-grey p-2">{t.thinking}</div> : null}
          </div>
          {error && <p className="text-red-600">Error: {error}</p>}
          <div className='flex flex-row gap-2 pt-6 max-w-full'>
            <div className='flex'>
            <input
              type="text"
              ref={inputRef} // Focus on text input when response is received
              placeholder={t.inputPlaceholder}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              className="bg-Nordea-light-grey pl-4 md:w-96 pr-14 rounded-full text-Nordea-text-dark-blue disabled:opacity-50"
            />
            <button
              onClick={() => handleMicrophoneClick()}
              className={`rounded-full -ml-11 cursor-pointer ${
                listening ? 'bg-Nordea-green' : 'bg-transparent md:hover:bg-Nordea-light-blue-2'
              }`}
            >
              {/* {loading ? 'Send' : 'Send'} {/* {loading ? 'Sending...' : 'Send'} */} 
              <svg className={`${listening ? 'fill-white' : 'fill-Nordea-text-dark-blue'} w-11 p-2`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44"><path d="M22 24.6999C20.7424 24.6999 19.678 24.2643 18.8068 23.3931C17.9356 22.5219 17.5 21.4575 17.5 20.1999V9.3999C17.5 8.1423 17.9356 7.0779 18.8068 6.2067C19.678 5.3355 20.7424 4.8999 22 4.8999C23.2576 4.8999 24.322 5.3355 25.1932 6.2067C26.0644 7.0779 26.5 8.1423 26.5 9.3999V20.1999C26.5 21.4575 26.0644 22.5219 25.1932 23.3931C24.322 24.2643 23.2576 24.6999 22 24.6999ZM20.65 37.7499V31.8167C17.68 31.4774 15.2125 30.2036 13.2475 27.9953C11.2825 25.7866 10.3 23.1882 10.3 20.1999H13C13 22.6899 13.8775 24.8124 15.6325 26.5674C17.3875 28.3224 19.51 29.1999 22 29.1999C24.49 29.1999 26.6125 28.3224 28.3675 26.5674C30.1225 24.8124 31 22.6899 31 20.1999H33.7C33.7 23.1882 32.7175 25.7866 30.7525 27.9953C28.7875 30.2036 26.32 31.4774 23.35 31.8167V37.7499H20.65Z"/></svg>
            </button>
            </div>
              <button 
              onClick={() => handleSend(false, message)}
              disabled={loading}
              className="bg-Nordea-text-dark-blue text-white rounded-full hover:bg-Nordea-accent-blue disabled:opacity-50 cursor-pointer"
              >
              
              <svg className="fill-white w-11 p-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M12.627 8.75H0.5V7.25H12.627L6.93075 1.55375L8 0.5L15.5 8L8 15.5L6.93075 14.4462L12.627 8.75Z"/></svg>
              </button>
          </div>
          <p className='text-Nordea-text-dark-blue opacity-70 text-sm'>{listeningCancelled ? null : listeningMessage}</p> {/* Show whether microphone is ready*/} 
        </div>
      </main>
    </div>
  );
}
