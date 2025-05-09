import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowRight, Users, Zap, ShieldCheck, TrendingUp, MessageCircle, Phone, Mail, User } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

const testimonials = [
  {
    name: 'Lucas Andrade',
    avatar: 'https://randomuser.me/api/portraits/men/32.jpg',
    text: 'Com os sinais NAÇÃO TRADER, finalmente consegui consistência e confiança nas minhas operações. Recomendo para todo trader sério!',
    result: '+R$ 4.200 em 2 meses'
  },
  {
    name: 'Marina Souza',
    avatar: 'https://randomuser.me/api/portraits/women/44.jpg',
    text: 'A interface é incrível e os sinais chegam em tempo real. O suporte me ajudou a tirar dúvidas desde o início.',
    result: 'Taxa de acerto: 81%'
  },
  {
    name: 'Carlos Lima',
    avatar: 'https://randomuser.me/api/portraits/men/65.jpg',
    text: 'Nunca imaginei que IA pudesse ser tão útil no day trade. O NAÇÃO TRADER mudou meu jogo!',
    result: 'ROI: 3,1x em 6 semanas'
  }
];

const faqs = [
  {
    q: 'Preciso ter experiência para usar o NAÇÃO TRADER?',
    a: 'Não! Nossa plataforma é intuitiva e pensada para todos os níveis. Você recebe sinais claros e pode aprender com a comunidade.'
  },
  {
    q: 'Os sinais são realmente em tempo real?',
    a: 'Sim! Utilizamos integrações diretas com o mercado e IA proprietária para entregar sinais instantâneos e de alta precisão.'
  },
  {
    q: 'Como funciona a garantia?',
    a: 'Se não gostar, basta cancelar a qualquer momento. Não há fidelidade e sua privacidade é garantida.'
  }
];

const AnimatedCounter: React.FC<{ end: number, label: string }> = ({ end, label }) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const duration = 1200;
    const step = Math.ceil(end / (duration / 16));
    const interval = setInterval(() => {
      start += step;
      if (start >= end) {
        setCount(end);
        clearInterval(interval);
      } else {
        setCount(start);
      }
    }, 16);
    return () => clearInterval(interval);
  }, [end]);
  return (
    <div className="flex flex-col items-center">
      <span className="text-3xl md:text-4xl font-extrabold text-[#00FF85] drop-shadow-lg">{count.toLocaleString('pt-BR')}</span>
      <span className="text-gray-300 text-sm mt-1">{label}</span>
    </div>
  );
};

const HERO_TITLE = 'Transforme seu Trading com a Nação Trader';
const HERO_SUBTITLE = 'Aumente sua taxa de acerto e receba sinais exclusivos em tempo real. Entre para a elite dos traders agora.';
const CTA_BUTTON = 'Quero Acesso Exclusivo aos Sinais Grátis';
const CTA_LOGIN = 'Já sou usuário';
const CTA_DASHBOARD = 'Acessar dashboard';
const BENEFITS = [
  {
    icon: <Zap size={32} className="mx-auto text-[#00FF85] animate-bounce" />, 
    title: 'Sinais Preditivos',
    desc: 'Aumente sua taxa de acerto com sinais baseados em IA e análise técnica avançada.'
  },
  {
    icon: <TrendingUp size={32} className="mx-auto text-[#FFD700] animate-pulse" />, 
    title: 'Resultados Comprovados',
    desc: 'Receba sinais exclusivos e veja sua performance evoluir com controle de risco.'
  },
  {
    icon: <Users size={32} className="mx-auto text-[#36A2EB] animate-spin-slow" />, 
    title: 'Comunidade Exclusiva',
    desc: 'Aprenda com outros traders, compartilhe estratégias e evolua mais rápido.'
  },
  {
    icon: <ShieldCheck size={32} className="mx-auto text-[#00FF85] animate-pulse" />, 
    title: 'Segurança e Privacidade',
    desc: 'Seus dados protegidos com criptografia e política de privacidade transparente.'
  }
];

const Welcome: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [scrollY, setScrollY] = useState(0);
  const [lead, setLead] = useState({ name: '', email: '', whatsapp: '' });
  const [leadStatus, setLeadStatus] = useState<'idle' | 'success' | 'error' | 'loading'>('idle');

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (typeof document !== 'undefined' && !document.getElementById('particles-style')) {
      const style = document.createElement('style');
      style.id = 'particles-style';
      style.innerHTML = `
        .particle { position: absolute; border-radius: 50%; opacity: 0.18; pointer-events: none; }
        .particle1 { width: 80px; height: 80px; background: #00FF85; left: 10vw; top: 20vh; animation: float1 8s infinite alternate; }
        .particle2 { width: 50px; height: 50px; background: #FFD700; right: 12vw; top: 30vh; animation: float2 10s infinite alternate; }
        .particle3 { width: 100px; height: 100px; background: #36A2EB; left: 40vw; bottom: 10vh; animation: float3 12s infinite alternate; }
        @keyframes float1 { 0% { transform: translateY(0); } 100% { transform: translateY(-40px); } }
        @keyframes float2 { 0% { transform: translateY(0); } 100% { transform: translateY(30px); } }
        @keyframes float3 { 0% { transform: translateY(0); } 100% { transform: translateY(-25px); } }
      `;
      document.head.appendChild(style);
    }
  }, []);

  const handleLeadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLead({ ...lead, [e.target.name]: e.target.value });
  };

  const handleLeadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLeadStatus('loading');
    
    try {
      // Validação básica dos campos
      if (!lead.email || !lead.name || !lead.whatsapp) {
        setLeadStatus('error');
        return;
      }
      
      // Inserir dados na tabela leads do Supabase
      const { error } = await supabase
        .from('leads')
        .insert([
          { 
            name: lead.name,
            email: lead.email,
            whatsapp: lead.whatsapp,
            source: 'landing_page' 
          }
        ]);
        
      if (error) {
        console.error('Erro ao salvar lead:', error);
        setLeadStatus('error');
        return;
      }
      
      // Sucesso: limpar formulário, mostrar mensagem
      setLeadStatus('success');
      setLead({ name: '', email: '', whatsapp: '' });
      
      // Redirecionar para tela de cadastro após 2 segundos
      setTimeout(() => {
        navigate('/register', { 
          state: { 
            email: lead.email,
            name: lead.name 
          }
        });
      }, 2000);
    } catch (err) {
      console.error('Erro inesperado:', err);
      setLeadStatus('error');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0A0A0A]">
      {/* HERO */}
      <div 
        className="relative h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-[#0A0A0A] via-[#101820] to-[#181818]"
        style={{
          background: `linear-gradient(rgba(10, 10, 10, 0.7), rgba(10, 10, 10, 0.9)), \
                       url('https://images.pexels.com/photos/6770610/pexels-photo-6770610.jpeg?auto=compress&cs=tinysrgb&w=1600') \
                       no-repeat center center`,
          backgroundSize: 'cover',
          backgroundAttachment: 'fixed',
          backgroundPosition: `center ${scrollY * 0.5}px`
        }}
      >
        {/* Partículas animadas */}
        <div className="particle particle1" />
        <div className="particle particle2" />
        <div className="particle particle3" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#0A0A0A] pointer-events-none"></div>
        <div className="z-10 text-center px-4 max-w-4xl mx-auto">
          <div className="flex justify-center mb-4">
            <span className="inline-flex items-center gap-2 bg-[#1E1E1E] text-[#FFD700] px-4 py-1 rounded-full text-xs font-semibold shadow border border-[#FFD700]/30 animate-pulse">
              <ShieldCheck size={16} /> Selo Nação Trader: Resultados & Alta Performance
            </span>
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold mb-6 text-white drop-shadow-lg leading-tight">
            {HERO_TITLE}
          </h1>
          <p className="text-2xl md:text-3xl mb-10 text-gray-200 font-medium">
            {HERO_SUBTITLE}
          </p>
          <form 
            onSubmit={handleLeadSubmit} 
            className="bg-black/30 backdrop-blur-md rounded-xl p-6 md:p-8 shadow-2xl mx-auto max-w-3xl border border-white/10"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 items-end">
              <div className="flex flex-col items-start">
                <label htmlFor="name" className="text-xs text-gray-400 mb-1 ml-1">Nome Completo</label>
                <div className="flex items-center gap-2 w-full bg-[#101820]/70 border border-[#333] rounded-lg px-3 py-2.5 focus-within:ring-1 focus-within:ring-[#00FF85]">
                  <User size={18} className="text-[#00FF85] opacity-70" />
                  <input
                    type="text"
                    id="name"
                    name="name"
                    placeholder="Seu nome"
                    value={lead.name}
                    onChange={handleLeadChange}
                    className="bg-transparent text-white focus:outline-none w-full placeholder-gray-500"
                    required
                  />
                </div>
              </div>
              <div className="flex flex-col items-start">
                <label htmlFor="email" className="text-xs text-gray-400 mb-1 ml-1">Seu Melhor E-mail</label>
                <div className="flex items-center gap-2 w-full bg-[#101820]/70 border border-[#333] rounded-lg px-3 py-2.5 focus-within:ring-1 focus-within:ring-[#00FF85]">
                  <Mail size={18} className="text-[#00FF85] opacity-70" />
                  <input
                    type="email"
                    id="email"
                    name="email"
                    placeholder="seu@email.com"
                    value={lead.email}
                    onChange={handleLeadChange}
                    className="bg-transparent text-white focus:outline-none w-full placeholder-gray-500"
                    required
                  />
                </div>
              </div>
              <div className="flex flex-col items-start">
                <label htmlFor="whatsapp" className="text-xs text-gray-400 mb-1 ml-1">WhatsApp (com DDD)</label>
                <div className="flex items-center gap-2 w-full bg-[#101820]/70 border border-[#333] rounded-lg px-3 py-2.5 focus-within:ring-1 focus-within:ring-[#00FF85]">
                  <Phone size={18} className="text-[#00FF85] opacity-70" />
                  <input
                    type="tel"
                    id="whatsapp"
                    name="whatsapp"
                    placeholder="(XX) XXXXX-XXXX"
                    value={lead.whatsapp}
                    onChange={handleLeadChange}
                    className="bg-transparent text-white focus:outline-none w-full placeholder-gray-500"
                    required
                  />
                </div>
              </div>
            </div>
            <button
              type="submit"
              className="w-full btn-primary px-6 py-3 text-lg font-bold flex items-center justify-center gap-2 transition-transform duration-150 hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl"
              disabled={leadStatus === 'loading'}
            >
              {leadStatus === 'loading' ? 'Enviando Inscrição...' : CTA_BUTTON}
              {leadStatus !== 'loading' && <ArrowRight size={22} />}
            </button>
          </form>
          {leadStatus === 'success' && (
            <div className="mt-4 text-green-400 font-semibold animate-fade-in bg-green-900/50 border border-green-700 rounded-md p-3 max-w-md mx-auto">
              ✓ Inscrição realizada! Redirecionando para criar sua conta...
            </div>
          )}
          {leadStatus === 'error' && (
            <div className="mt-4 text-red-400 font-semibold animate-fade-in bg-red-900/50 border border-red-700 rounded-md p-3 max-w-md mx-auto">
              ⚠ Ops! Não foi possível salvar seus dados. Verifique se todos os campos foram preenchidos corretamente.
            </div>
          )}
          <div className="flex flex-col sm:flex-row justify-center gap-4 mt-10">
            {user ? (
              <Link 
                to="/dashboard" 
                className="btn-secondary flex items-center justify-center gap-2"
              >
                {CTA_DASHBOARD} <ArrowRight size={20} />
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-secondary">
                  {CTA_LOGIN}
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* CONTADORES */}
      <div className="bg-[#101820] py-10">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-around gap-8">
          <AnimatedCounter end={12450} label="Traders Impactados" />
          <AnimatedCounter end={98} label="Taxa de Satisfação (%)" />
          <AnimatedCounter end={320000} label="Sinais Exclusivos Enviados" />
        </div>
      </div>

      {/* BENEFÍCIOS */}
      <div className="bg-[#0A0A0A] py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center text-white">
            Por que escolher a <span className="text-[#00FF85]">Nação Trader</span>?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {BENEFITS.map((b, i) => (
              <div key={i} className="card hover:border-[#00FF85] transition-all duration-300 text-center">
                {b.icon}
                <h3 className="text-lg font-semibold mt-4 mb-2">{b.title}</h3>
                <p className="text-gray-400">{b.desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-12 text-center">
            <span className="inline-block bg-[#00FF85]/10 text-[#00FF85] px-6 py-3 rounded-full font-bold text-lg shadow border border-[#00FF85]/30 animate-pulse">
              Aumente sua taxa de acerto. Receba sinais exclusivos. Potencialize seus resultados.
            </span>
          </div>
        </div>
      </div>

      {/* DEPOIMENTOS */}
      <div className="bg-[#101820] py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold mb-10 text-center text-[#FFD700]">O que dizem os traders NAÇÃO TRADER</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((t, i) => (
              <div key={i} className="bg-[#181818] rounded-xl p-6 shadow-lg border border-[#222] flex flex-col items-center text-center">
                <img src={t.avatar} alt={t.name} className="w-16 h-16 rounded-full mb-3 border-2 border-[#00FF85] object-cover" />
                <h3 className="font-semibold text-lg text-white mb-1">{t.name}</h3>
                <span className="text-xs text-[#FFD700] mb-2">{t.result}</span>
                <p className="text-gray-300 text-sm">"{t.text}"</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* FAQ */}
      <div className="bg-[#0A0A0A] py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-8 text-center text-[#00FF85]">Perguntas Frequentes</h2>
          <div className="space-y-6">
            {faqs.map((faq, i) => (
              <div key={i} className="bg-[#181818] rounded-lg p-5 border border-[#222]">
                <h3 className="font-semibold text-lg text-[#FFD700] mb-2">{faq.q}</h3>
                <p className="text-gray-300 text-base">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* RODAPÉ */}
      <footer className="bg-[#121212] py-8 border-t border-[#222222]">
        <div className="max-w-6xl mx-auto px-4 text-center text-gray-400">
          <div className="flex flex-col md:flex-row justify-center gap-6 mb-4">
            <a href="#" className="hover:text-[#00FF85] transition">Termos de Uso</a>
            <a href="#" className="hover:text-[#00FF85] transition">Política de Privacidade</a>
            <a href="#" className="hover:text-[#00FF85] transition">Contato</a>
            <a href="#" className="hover:text-[#FFD700] transition">Instagram</a>
            <a href="#" className="hover:text-[#36A2EB] transition">Telegram</a>
          </div>
          <p>© 2025 Nação Trader. Todos os direitos reservados.</p>
          <p className="mt-2 text-sm">
            As informações fornecidas são apenas para fins educacionais e não constituem aconselhamento financeiro.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Welcome;