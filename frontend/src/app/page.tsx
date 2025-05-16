'use client';
import React, { useState, useRef, useEffect } from 'react';

//import Image from "next/image";

// This is the home page of the application. This is React code with TypeScript enabled and Tailwind CSS.
// Tailwind CSS makes it easy to style the UI by using breakpoints to form a mobile-first, responsive layout with inline styles. 

type Message = {
  sender: 'User' | 'Assistant';
  text: string;
};

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generate a unique user ID for each session.
  // This way, the backend will be able to handle multiple users at the same time.
  const [userId] = useState<string | null>(crypto.randomUUID());
  const inputRef = useRef<HTMLInputElement>(null); // Create input ref
  const messageLogRef = useRef<HTMLDivElement>(null); // Ref for message log

  const handleSend = async () => {
    if (!message.trim()) return; // prevent sending empty messages
    setLoading(true);
    setError(null);

    // Add user message to log
    setMessages((prev) => [...prev, { sender: 'User', text: message }]);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, { // process.env.NEXT_PUBLIC makes the environment variable available in the browser (it is public)
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, userId }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const data = await res.json();
      setMessages((prev) => [...prev, { sender: 'Assistant', text: data.response }]);
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
      handleSend();
    }
  };

  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus(); // Focus on the input field after receiving a response, so the user can immediately type a new message
    }
    // Scroll message log to bottom when messages change
    if (messageLogRef.current) {
      messageLogRef.current.scrollTop = messageLogRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-[32px] row-start-2 items-center">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-[-.01em] text-center text-Nordea-text-dark-blue">
          Smart Bank Chatbot
        </h1>
        <p className="text-sm/6 text-center font-[family-name:var(--font-geist-mono)] text-Nordea-text-dark-blue">
          A new generation of banking <br /> services is here.
        </p>
        
        <div className="flex flex-col gap-2 w-full items-center">
          {/* Message log */}
          <div
            className="flex flex-col gap-2 max-md:w-full md:w-96 max-h-96 overflow-y-scroll pb-4"
            ref={messageLogRef}
            style={{
              scrollbarWidth: messages.length > 5 ? 'auto' : 'none', // Chrome, Firefox, Safari, Edge
              msOverflowStyle: messages.length > 5 ? 'auto' : 'none',
            }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-3xl ${
                  msg.sender === 'User'
                    ? 'bg-Nordea-text-dark-blue text-white self-end'
                    : 'bg-Nordea-light-blue-1 text-Nordea-text-dark-blue self-start'
                }`}
              >
                <strong>{msg.sender}:</strong> {msg.text}
              </div>
            ))}
          </div>

          {error && <p className="text-red-600">Error: {error}</p>}
          <div className='flex flex-row gap-1'>
          <input
            type="text"
            ref={inputRef} // Focus on text input when response is received
            placeholder="Ask a question..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="bg-Nordea-grey px-4 rounded-full text-Nordea-text-dark-blue disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="bg-Nordea-text-dark-blue text-white px-4 py-2 rounded-full hover:bg-Nordea-accent-blue disabled:opacity-50 cursor-pointer"
          >
            {loading ? 'Send' : 'Send'} {/* {loading ? 'Sending...' : 'Send'} */}
            {/* <svg className="fill-white w-14 p-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M12.627 8.75H0.5V7.25H12.627L6.93075 1.55375L8 0.5L15.5 8L8 15.5L6.93075 14.4462L12.627 8.75Z"/></svg>
           */}</button>
          <button className='bg-Nordea-text-dark-blue rounded-full hover:bg-Nordea-accent-blue cursor-pointer'>
            <svg className="fill-white w-10 p-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44"><path d="M22 24.6999C20.7424 24.6999 19.678 24.2643 18.8068 23.3931C17.9356 22.5219 17.5 21.4575 17.5 20.1999V9.3999C17.5 8.1423 17.9356 7.0779 18.8068 6.2067C19.678 5.3355 20.7424 4.8999 22 4.8999C23.2576 4.8999 24.322 5.3355 25.1932 6.2067C26.0644 7.0779 26.5 8.1423 26.5 9.3999V20.1999C26.5 21.4575 26.0644 22.5219 25.1932 23.3931C24.322 24.2643 23.2576 24.6999 22 24.6999ZM20.65 37.7499V31.8167C17.68 31.4774 15.2125 30.2036 13.2475 27.9953C11.2825 25.7866 10.3 23.1882 10.3 20.1999H13C13 22.6899 13.8775 24.8124 15.6325 26.5674C17.3875 28.3224 19.51 29.1999 22 29.1999C24.49 29.1999 26.6125 28.3224 28.3675 26.5674C30.1225 24.8124 31 22.6899 31 20.1999H33.7C33.7 23.1882 32.7175 25.7866 30.7525 27.9953C28.7875 30.2036 26.32 31.4774 23.35 31.8167V37.7499H20.65Z"/></svg>
          </button>
          </div>
        </div>
      </main>
    </div>
  );
}
