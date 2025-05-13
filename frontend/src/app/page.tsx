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
  }, [messages]);

  return (
    <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-[-.01em] text-center sm:text-left">
          Smart Bank Chatbot
        </h1>
        <p className="text-sm/6 text-center sm:text-left font-[family-name:var(--font-geist-mono)]">
          A new generation of banking services is here.
        </p>
        
        <div className="flex flex-col gap-4 w-full max-w-md">
          {/* Message log */}
          <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-3 rounded ${
                  msg.sender === 'User'
                    ? 'bg-blue-600 text-white self-end'
                    : 'bg-gray-800 text-white self-start'
                }`}
              >
                <strong>{msg.sender}:</strong> {msg.text}
              </div>
            ))}
          </div>

          {error && <p className="text-red-600">Error: {error}</p>}
          <input
            type="text"
            ref={inputRef} // Focus on text input when response is received
            placeholder="Ask a question..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="bg-gray-700 border border-gray-400 p-2 rounded text-white disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="bg-green-600 text-white px-4 py-2 rounded-2xl hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </main>
    </div>
  );
}
