import React from 'react';
import { Link } from 'react-router-dom';
import logoImg from '../imgs/logo.png';

const Navbar: React.FC = () => {
  return (
    <nav className="bg-gradient-to-r from-[#101820] via-[#181818] to-[#0A0A0A] border-b border-[#222222] fixed top-0 left-0 right-0 z-40 shadow-lg">
      <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center h-20">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center group">
              <div className="rounded-full bg-[#0A0A0A] p-2 shadow-lg border-2 border-[#00FF85] mr-3 ml-12 md:ml-0 flex items-center justify-center">
                <img src={logoImg} alt="Nação Trader Logo" className="h-14 w-14 object-contain drop-shadow-[0_0_12px_#00FF85] group-hover:scale-105 transition-transform duration-200" />
              </div>
              <span className="text-3xl font-extrabold text-[#00FF85] drop-shadow-lg tracking-tight group-hover:text-white transition-colors duration-200">
                Nação Trader
              </span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;