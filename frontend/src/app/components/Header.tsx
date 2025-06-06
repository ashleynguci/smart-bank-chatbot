'use client'

import Image from 'next/image'
import { useLanguage } from '../context/LanguageContext'

export default function Header() {
  const { language, setLanguage } = useLanguage();

  const toggleLanguage = () => {
    if (language === 'EN') {
      setLanguage('FI');
    } else {
      setLanguage('EN');
    }
  };

  return (
    <header className="w-full flex flex-row justify-between items-center px-2 fixed bg-white fill-Nordea-text-dark-blue">
      <button 
        className={`rounded-full bg-Nordea-grey cursor-pointer`}
        >
        <svg className=" w-11 p-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M3.373 7.25L15.5 7.25L15.5 8.75L3.373 8.75L9.06925 14.4462L8 15.5L0.500001 8L8 0.499999L9.06925 1.55375L3.373 7.25Z"/></svg>
      </button>
      <Image
        src="/nordea_logo1.png"
        alt="Nordea Logo"
        width={140}
        height={70}
        className="object-contain p-3"
        priority
        />
      {/* <button 
        className={`rounded-full bg-Nordea-grey cursor-pointer`}
        >
        <svg className="w-11 p-3 py-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 15 3"><path d="M1.5 3C1.0875 3 0.734417 2.85308 0.44075 2.55925C0.146917 2.26558 0 1.9125 0 1.5C0 1.0875 0.146917 0.734417 0.44075 0.44075C0.734417 0.146917 1.0875 0 1.5 0C1.9125 0 2.26567 0.146917 2.5595 0.44075C2.85317 0.734417 3 1.0875 3 1.5C3 1.9125 2.85317 2.26558 2.5595 2.55925C2.26567 2.85308 1.9125 3 1.5 3ZM7.26925 3C6.85675 3 6.50367 2.85308 6.21 2.55925C5.91617 2.26558 5.76925 1.9125 5.76925 1.5C5.76925 1.0875 5.91617 0.734417 6.21 0.44075C6.50367 0.146917 6.85675 0 7.26925 0C7.68175 0 8.03483 0.146917 8.3285 0.44075C8.62233 0.734417 8.76925 1.0875 8.76925 1.5C8.76925 1.9125 8.62233 2.26558 8.3285 2.55925C8.03483 2.85308 7.68175 3 7.26925 3ZM13.0385 3C12.626 3 12.2728 2.85308 11.979 2.55925C11.6853 2.26558 11.5385 1.9125 11.5385 1.5C11.5385 1.0875 11.6853 0.734417 11.979 0.44075C12.2728 0.146917 12.626 0 13.0385 0C13.451 0 13.8041 0.146917 14.0978 0.44075C14.3916 0.734417 14.5385 1.0875 14.5385 1.5C14.5385 1.9125 14.3916 2.26558 14.0978 2.55925C13.8041 2.85308 13.451 3 13.0385 3Z"/></svg>
      </button> */}
      <button 
        onClick={toggleLanguage}
        className={`rounded-full bg-Nordea-grey cursor-pointer p-2 w-11 h-11 text-lg font-bold text-Nordea-text-dark-blue`}>
        {language}
      </button>
    </header>
  );
}