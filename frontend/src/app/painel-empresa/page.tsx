'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { BrasilLogo } from '@/components/BrasilLogo';
import { 
  Building2, 
  MessageCircle, 
  Phone, 
  Eye, 
  Clock, 
  TrendingUp, 
  Pause, 
  Play, 
  ShieldAlert, 
  ShieldCheck, 
  CheckCircle2, 
  Save, 
  ArrowLeft, 
  ExternalLink,
  Sliders,
  AlertTriangle,
  Award,
  Star,
  MapPin,
  Lock,
  FileText,
  Upload,
  Image as ImageIcon,
  LogOut,
  Smartphone,
  KeyRound,
  RefreshCw,
  Loader2,
  Store,
  Navigation,
  Globe
} from 'lucide-react';
import { Suspense } from 'react';
import ManifestoModal from '@/components/ManifestoModal';

interface OwnerBusiness {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  listing_type: string;
  service_mode: 'at_customer' | 'at_location' | 'both' | 'online';
  service_radius_km?: number | null;
  serves_at_location?: boolean;
  serves_at_customer?: boolean;
  serves_online?: boolean;
  whatsapp: string;
  phone?: string | null;
  website?: string | null;
  instagram?: string | null;
  street?: string | null;
  number?: string | null;
  neighborhood: string;
  city: string;
  state: string;
  postal_code?: string | null;
  show_full_address: boolean;
  logo_url?: string | null;
  banner_url?: string | null;
  status: 'approved' | 'pending_review' | 'suspended' | 'rejected';
  is_verified: boolean;
  created_at?: string;
  manifesto_version?: string;
}

export default function BusinessDashboardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#070b0e] text-slate-400 p-8 text-center text-xs">Carregando painel da empresa...</div>}>
      <BusinessDashboardContent />
    </Suspense>
  );
}

function BusinessDashboardContent() {
  const searchParams = useSearchParams();
  const requestedBizId = searchParams?.get('bizId');

  // Sessão do Proprietário
  const [session, setSession] = useState<{
    token: string;
    user: { id: string; name: string; email: string; role: string };
  } | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = sessionStorage.getItem('patriotaindica_owner_session');
      if (saved) {
        try { return JSON.parse(saved); } catch {}
      }
    }
    return null;
  });

  // Estado do Login
  const [loginTab, setLoginTab] = useState<'whatsapp' | 'email'>('whatsapp');
  const [whatsappPhone, setWhatsappPhone] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpTargetBizId, setOtpTargetBizId] = useState<string | null>(null);
  const [otpMaskedPhone, setOtpMaskedPhone] = useState<string | null>(null);
  const [otpDevCode, setOtpDevCode] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Lista de empresas gerenciadas pelo dono
  const [businesses, setBusinesses] = useState<OwnerBusiness[]>([]);
  const [selectedBizId, setSelectedBizId] = useState<string>('');
  const [loadingBiz, setLoadingBiz] = useState(false);

  // Modal da Carta de Princípios
  const [showManifestoModal, setShowManifestoModal] = useState(false);

  // Campos do formulário de edição
  const [description, setDescription] = useState('');
  const [instagram, setInstagram] = useState('');
  const [website, setWebsite] = useState('');
  const [phone, setPhone] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [neighborhood, setNeighborhood] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('SP');
  const [serviceMode, setServiceMode] = useState<'at_customer' | 'at_location' | 'both' | 'online'>('at_customer');
  const [servesAtLocation, setServesAtLocation] = useState<boolean>(true);
  const [servesAtCustomer, setServesAtCustomer] = useState<boolean>(true);
  const [servesOnline, setServesOnline] = useState<boolean>(false);
  const [serviceRadiusKm, setServiceRadiusKm] = useState<number>(20);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [bannerUrl, setBannerUrl] = useState<string | null>(null);

  // Status e feedback
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [currentStatus, setCurrentStatus] = useState<string>('approved');
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveLoading, setSaveLoading] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingBanner, setUploadingBanner] = useState(false);

  const logoInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);

  // Sincronizar dados da empresa selecionada
  const activeBusiness = businesses.find((b) => b.id === selectedBizId) || businesses[0] || null;

  useEffect(() => {
    if (activeBusiness) {
      setDescription(activeBusiness.description || '');
      setInstagram(activeBusiness.instagram || '');
      setWebsite(activeBusiness.website || '');
      setPhone(activeBusiness.phone || '');
      setWhatsapp(activeBusiness.whatsapp || '');
      setNeighborhood(activeBusiness.neighborhood || '');
      setCity(activeBusiness.city || '');
      setState(activeBusiness.state || 'SP');
      setServiceMode(activeBusiness.service_mode || 'at_customer');
      setServesAtLocation(
        activeBusiness.serves_at_location !== undefined
          ? activeBusiness.serves_at_location
          : activeBusiness.service_mode === 'at_location' || activeBusiness.service_mode === 'both'
      );
      setServesAtCustomer(
        activeBusiness.serves_at_customer !== undefined
          ? activeBusiness.serves_at_customer
          : activeBusiness.service_mode === 'at_customer' || activeBusiness.service_mode === 'both'
      );
      setServesOnline(
        activeBusiness.serves_online !== undefined
          ? activeBusiness.serves_online
          : activeBusiness.service_mode === 'online'
      );
      setServiceRadiusKm(activeBusiness.service_radius_km || 20);
      setLogoUrl(activeBusiness.logo_url || null);
      setBannerUrl(activeBusiness.banner_url || null);
      setCurrentStatus(activeBusiness.status);
      setIsPaused(activeBusiness.status === 'suspended');
    }
  }, [activeBusiness]);

  // Carregar negócios do proprietário autenticado
  const fetchMyBusinesses = async (token: string) => {
    setLoadingBiz(true);
    try {
      const res = await fetch('/api/v1/owner/my-businesses', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setBusinesses(data);
        if (data.length > 0) {
          const matched = requestedBizId && data.some((b: OwnerBusiness) => b.id === requestedBizId)
            ? requestedBizId
            : data[0].id;
          setSelectedBizId(matched);
        }
      }
    } catch (err) {
      console.error('Erro ao carregar empresas do proprietário:', err);
    } finally {
      setLoadingBiz(false);
    }
  };

  useEffect(() => {
    if (session?.token) {
      fetchMyBusinesses(session.token);
    }
  }, [session]);

  // Login por WhatsApp (Passo 1: Enviar OTP)
  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);

    try {
      const res = await fetch('/api/v1/claim/request-otp-by-phone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: whatsappPhone }),
      });

      const data = await res.json();
      if (!res.ok) {
        setAuthError(data.detail || 'Não foi possível enviar o código para este WhatsApp.');
        setAuthLoading(false);
        return;
      }

      setOtpSent(true);
      setOtpTargetBizId(data.business_id);
      setOtpMaskedPhone(data.masked_phone);
      if (data.dev_code) {
        setOtpDevCode(data.dev_code);
        setOtpCode(data.dev_code);
      }
      setAuthLoading(false);
    } catch (err) {
      setAuthError('Falha de conexão com o servidor. Tente novamente.');
      setAuthLoading(false);
    }
  };

  // Login por WhatsApp (Passo 2: Confirmar OTP)
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpTargetBizId) return;

    setAuthLoading(true);
    setAuthError(null);

    try {
      const res = await fetch(`/api/v1/claim/${otpTargetBizId}/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: otpCode.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        setAuthError(data.detail || 'Código de confirmação inválido ou expirado.');
        setAuthLoading(false);
        return;
      }

      const newSession = {
        token: data.access_token,
        user: data.user,
      };

      sessionStorage.setItem('patriotaindica_owner_session', JSON.stringify(newSession));
      document.cookie = `owner_session=${data.access_token}; path=/; SameSite=Strict; max-age=86400`;
      setSession(newSession);
      setAuthLoading(false);
    } catch (err) {
      setAuthError('Erro ao validar o código. Tente novamente.');
      setAuthLoading(false);
    }
  };

  // Login por E-mail e Senha
  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);

    try {
      const formData = new URLSearchParams();
      formData.append('username', loginEmail.trim().toLowerCase());
      formData.append('password', loginPassword);

      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });

      const data = await res.json();
      if (!res.ok) {
        setAuthError(data.detail || 'E-mail ou senha incorretos.');
        setAuthLoading(false);
        return;
      }

      const newSession = {
        token: data.access_token,
        user: {
          id: data.user.id,
          name: data.user.name,
          email: data.user.email,
          role: data.user.role,
        },
      };

      sessionStorage.setItem('patriotaindica_owner_session', JSON.stringify(newSession));
      document.cookie = `owner_session=${data.access_token}; path=/; SameSite=Strict; max-age=86400`;
      setSession(newSession);
      setAuthLoading(false);
    } catch (err) {
      setAuthError('Falha ao autenticar. Tente novamente.');
      setAuthLoading(false);
    }
  };

  // Logout
  const handleLogout = () => {
    sessionStorage.removeItem('patriotaindica_owner_session');
    document.cookie = 'owner_session=; path=/; max-age=0';
    setSession(null);
    setBusinesses([]);
    setOtpSent(false);
    setOtpCode('');
  };

  // Toggle Pausar / Reativar Anúncio
  const handleTogglePause = async () => {
    if (!activeBusiness || !session) return;

    try {
      const res = await fetch(`/api/v1/owner/${activeBusiness.id}/toggle-pause`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.token}`,
        },
      });

      const data = await res.json();
      if (res.ok) {
        setIsPaused(data.status === 'suspended');
        setCurrentStatus(data.status);
        setSaveSuccess(data.message);
        setTimeout(() => setSaveSuccess(null), 5000);
      } else {
        alert(data.detail || 'Não foi possível alterar o status do anúncio.');
      }
    } catch (err) {
      alert('Erro de conexão com o servidor.');
    }
  };

  // Upload de Imagens (Logo ou Banner)
  const handleUploadImage = async (type: 'logo' | 'banner', e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !session || !activeBusiness) return;

    if (type === 'logo') setUploadingLogo(true);
    else setUploadingBanner(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/v1/media/upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.token}`,
        },
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.url) {
        if (type === 'logo') {
          setLogoUrl(data.url);
          // Persistir no backend
          await fetch(`/api/v1/owner/${activeBusiness.id}/profile`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${session.token}`,
            },
            body: JSON.stringify({ logo_url: data.url }),
          });
        } else {
          setBannerUrl(data.url);
          // Persistir no backend
          await fetch(`/api/v1/owner/${activeBusiness.id}/profile`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${session.token}`,
            },
            body: JSON.stringify({ banner_url: data.url }),
          });
        }
        setSaveSuccess(`${type === 'logo' ? 'Logotipo' : 'Foto de capa'} atualizado com sucesso!`);
        setTimeout(() => setSaveSuccess(null), 4000);
      } else {
        alert(data.detail || 'Falha no envio da imagem.');
      }
    } catch (err) {
      alert('Erro de rede ao enviar arquivo.');
    } finally {
      if (type === 'logo') setUploadingLogo(false);
      else setUploadingBanner(false);
    }
  };

  // Salvar Alterações de Perfil
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeBusiness || !session) return;

    setSaveLoading(true);
    setSaveSuccess(null);

    if (!servesAtLocation && !servesAtCustomer && !servesOnline) {
      alert('Selecione ao menos uma forma de atendimento (No Estabelecimento, A Domicílio ou Online).');
      setSaveLoading(false);
      return;
    }

    let effectiveMode: 'at_location' | 'at_customer' | 'both' | 'online' = 'at_location';
    if (servesAtCustomer && servesAtLocation) {
      effectiveMode = 'both';
    } else if (servesAtCustomer) {
      effectiveMode = 'at_customer';
    } else if (servesOnline && !servesAtLocation) {
      effectiveMode = 'online';
    }

    try {
      const payload = {
        description: description.trim(),
        instagram: instagram.trim() || null,
        website: website.trim() || null,
        phone: phone.trim() || null,
        whatsapp: whatsapp.trim(),
        neighborhood: neighborhood.trim(),
        city: city.trim(),
        state: state.trim().toUpperCase(),
        service_mode: effectiveMode,
        serves_at_location: servesAtLocation,
        serves_at_customer: servesAtCustomer,
        serves_online: servesOnline,
        service_radius_km: servesAtCustomer ? (serviceRadiusKm || 20) : null,
        logo_url: logoUrl,
        banner_url: bannerUrl,
      };

      const res = await fetch(`/api/v1/owner/${activeBusiness.id}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        setCurrentStatus(data.status);
        setIsPaused(data.status === 'suspended');
        setSaveSuccess(data.message);
        setTimeout(() => setSaveSuccess(null), 6000);
      } else {
        alert(data.detail || 'Erro ao salvar alterações.');
      }
    } catch (err) {
      alert('Erro de conexão ao salvar perfil.');
    } finally {
      setSaveLoading(false);
    }
  };

  // TELA DE LOGIN (Se não estiver autenticado)
  if (!session) {
    return (
      <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col items-center justify-center p-4 font-sans selection:bg-amber-500 selection:text-black">
        <div className="w-full max-w-md p-6 sm:p-8 rounded-2xl bg-[#0d151c] border border-[#182836] shadow-2xl space-y-6">
          <div className="text-center space-y-2">
            <div className="flex justify-center mb-3">
              <BrasilLogo size={44} className="w-11 h-11 !rounded-xl" />
            </div>
            <h1 className="text-xl font-black text-white tracking-tight flex items-center justify-center gap-2">
              Painel do Empresário
            </h1>
            <p className="text-xs text-slate-400">
              Acesse a gestão do seu anúncio, métricas de WhatsApp e fotos no Patriota Indica.
            </p>
          </div>

          {/* Seletor de Métodos de Login */}
          <div className="grid grid-cols-2 p-1 rounded-xl bg-[#070b0e] border border-[#182836] text-xs font-semibold">
            <button
              type="button"
              onClick={() => { setLoginTab('whatsapp'); setAuthError(null); }}
              className={`py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                loginTab === 'whatsapp'
                  ? 'bg-amber-500 text-black shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Smartphone className="w-3.5 h-3.5" />
              WhatsApp (Sem Senha)
            </button>
            <button
              type="button"
              onClick={() => { setLoginTab('email'); setAuthError(null); }}
              className={`py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                loginTab === 'email'
                  ? 'bg-amber-500 text-black shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              E-mail e Senha
            </button>
          </div>

          {/* Feedback de Erro */}
          {authError && (
            <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs flex items-center gap-2 animate-in fade-in">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{authError}</span>
            </div>
          )}

          {/* Aba 1: WhatsApp OTP */}
          {loginTab === 'whatsapp' && (
            <div>
              {!otpSent ? (
                <form onSubmit={handleRequestOtp} className="space-y-4 text-xs">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">
                      WhatsApp Cadastrado da Empresa
                    </label>
                    <input
                      required
                      type="text"
                      placeholder="DDD + Número (ex: 19999998888)"
                      value={whatsappPhone}
                      onChange={(e) => setWhatsappPhone(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none text-sm"
                    />
                    <span className="text-[11px] text-slate-500 mt-1 block">
                      Enviaremos um código de 6 dígitos direto para o seu WhatsApp oficial.
                    </span>
                  </div>

                  <button
                    type="submit"
                    disabled={authLoading}
                    className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-black text-xs transition-all shadow-lg shadow-amber-950/40 flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {authLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4 fill-black" />}
                    {authLoading ? 'Verificando...' : 'Receber Código no WhatsApp'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyOtp} className="space-y-4 text-xs">
                  <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 text-amber-300 text-xs space-y-1">
                    <p>Código enviado para <strong className="font-mono text-white">{otpMaskedPhone}</strong>.</p>
                    {otpDevCode ? (
                      <p className="text-[11px] text-emerald-400 font-mono">
                        Ambiente de teste: Código <strong>{otpDevCode}</strong> (ou utilize <strong>123456</strong>)
                      </p>
                    ) : (
                      <p className="text-[11px] text-slate-400">
                        Dica de teste: Você também pode usar <strong>123456</strong> em modo de homologação.
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-slate-300 font-medium mb-1">
                      Código de Confirmação (6 dígitos)
                    </label>
                    <input
                      required
                      type="text"
                      maxLength={6}
                      placeholder="000000"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none font-mono text-center tracking-widest text-lg"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={authLoading || otpCode.length < 6}
                    className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-black text-xs transition-all shadow-lg shadow-amber-950/40 flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {authLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    {authLoading ? 'Validando...' : 'Confirmar e Acessar Painel'}
                  </button>

                  <button
                    type="button"
                    onClick={() => { setOtpSent(false); setOtpCode(''); }}
                    className="w-full text-center text-xs text-slate-400 hover:text-white underline pt-1"
                  >
                    Digitar outro número de WhatsApp
                  </button>
                </form>
              )}
            </div>
          )}

          {/* Aba 2: E-mail e Senha */}
          {loginTab === 'email' && (
            <form onSubmit={handleEmailLogin} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">E-mail Cadastrado</label>
                <input
                  required
                  type="email"
                  placeholder="seu@email.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Senha</label>
                <input
                  required
                  type="password"
                  placeholder="••••••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-black text-xs transition-all shadow-lg shadow-amber-950/40 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {authLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
                {authLoading ? 'Entrando...' : 'Entrar no Painel'}
              </button>
            </form>
          )}

          <div className="pt-2 text-center border-t border-[#182836]">
            <Link
              href="/"
              className="text-xs text-slate-400 hover:text-amber-400 flex items-center justify-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Voltar ao Marketplace Principal
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // TELA PRINCIPAL AUTENTICADA DO EMPRESÁRIO
  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-black">
      {/* Top Navbar */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-2 text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] hover:border-amber-500/50 text-slate-300 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Ver Marketplace</span>
            </Link>
            <div className="h-5 w-[1px] bg-[#182836]" />
            <div className="flex items-center gap-2">
              <BrasilLogo size={28} className="w-7 h-7 !rounded-lg" />
              <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                Painel da Empresa
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  {session.user.role === 'admin' ? 'Administrador' : 'Lojista'}
                </span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {businesses.length > 1 && (
              <select
                value={selectedBizId}
                onChange={(e) => setSelectedBizId(e.target.value)}
                className="px-3 py-1.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none max-w-[180px] sm:max-w-xs truncate"
              >
                {businesses.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={handleLogout}
              title="Encerrar sessão"
              className="p-2 rounded-xl bg-[#070b0e] border border-[#182836] hover:border-red-500/50 text-slate-400 hover:text-red-400 transition-colors flex items-center gap-1.5 text-xs font-medium"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Sair</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 py-8 flex-1 w-full space-y-6">
        {loadingBiz && (
          <div className="p-4 rounded-xl bg-[#0d151c] text-center text-xs text-slate-400 flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
            Carregando dados da sua empresa...
          </div>
        )}

        {!activeBusiness && !loadingBiz ? (
          <div className="p-8 rounded-2xl bg-[#0d151c] border border-[#182836] text-center space-y-3">
            <Building2 className="w-10 h-10 text-slate-500 mx-auto" />
            <h2 className="text-base font-bold text-white">Nenhuma empresa vinculada a esta conta</h2>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Se você acabou de cadastrar sua empresa, use a opção de acesso por WhatsApp informando o número cadastrado para vinculá-la automaticamente.
            </p>
            <button
              onClick={handleLogout}
              className="px-4 py-2 rounded-xl bg-amber-500 text-black text-xs font-bold"
            >
              Fazer login com outro número
            </button>
          </div>
        ) : activeBusiness ? (
          <>
            {/* Banner de Status e Controle */}
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    {activeBusiness.listing_type === 'product' ? 'Produtos' : activeBusiness.listing_type === 'both' ? 'Produtos & Serviços' : 'Prestação de Serviços'}
                  </span>

                  {currentStatus === 'approved' && !isPaused && (
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Anúncio Ativo na Busca
                    </span>
                  )}

                  {isPaused && (
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                      <Pause className="w-3.5 h-3.5 text-amber-400" />
                      Anúncio Pausado pelo Dono
                    </span>
                  )}

                  {currentStatus === 'pending_review' && (
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-amber-400" />
                      Reanálise em Andamento
                    </span>
                  )}
                </div>

                <h2 className="text-2xl font-black text-white">{activeBusiness.name}</h2>
                <p className="text-xs text-slate-400 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-amber-400" />
                  {activeBusiness.neighborhood}, {activeBusiness.city} - {activeBusiness.state}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Toggle de Pausa do Anúncio */}
                <button
                  type="button"
                  onClick={handleTogglePause}
                  className={`px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
                    isPaused
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md'
                      : 'bg-[#182836] hover:bg-[#253d52] text-amber-300 border border-amber-500/30'
                  }`}
                >
                  {isPaused ? <Play className="w-4 h-4 fill-white" /> : <Pause className="w-4 h-4 fill-amber-300" />}
                  {isPaused ? 'Reativar Anúncio' : 'Pausar Anúncio'}
                </button>

                <Link
                  href={`/${activeBusiness.city.toLowerCase()}-${activeBusiness.state.toLowerCase()}/servicos/${activeBusiness.slug}`}
                  target="_blank"
                  className="px-4 py-2.5 rounded-xl bg-[#070b0e] hover:bg-[#121e29] border border-[#182836] text-xs font-medium text-slate-200 hover:text-white flex items-center gap-1.5 transition-colors"
                >
                  Ver Perfil Público
                  <ExternalLink className="w-3.5 h-3.5 text-amber-400" />
                </Link>
              </div>
            </div>

            {/* Banner da Carta de Princípios */}
            <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-950/25 via-[#0d151c] to-emerald-950/25 border border-amber-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                  <Award className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-bold text-white text-xs sm:text-sm flex items-center gap-2">
                    Empresa Signatária Oficial • Patriota Indica
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono">
                      v1.0-2026
                    </span>
                  </p>
                  <p className="text-slate-400 text-xs">
                    Seu negócio ostenta publicamente o selo de honra da Livre Iniciativa, Propriedade Privada e Ética Cristã/Ocidental.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowManifestoModal(true)}
                className="px-3.5 py-1.5 rounded-xl border border-amber-500/40 text-amber-300 hover:bg-amber-500/15 text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5"
              >
                <FileText className="w-3.5 h-3.5" />
                Ver Carta Completa
              </button>
            </div>

            {/* Notificações e Alertas */}
            {saveSuccess && (
              <div className="p-4 rounded-xl bg-emerald-950/70 border border-emerald-500/60 text-emerald-300 text-xs flex items-center gap-2 shadow-lg animate-in fade-in">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>{saveSuccess}</span>
              </div>
            )}

            {/* SEÇÃO DE GESTÃO DE IMAGENS (Logo e Capa/Banner) */}
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-4 shadow-xl">
              <div className="pb-3 border-b border-[#182836] flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <ImageIcon className="w-4 h-4 text-amber-400" />
                    Identidade Visual (Logotipo e Foto de Capa)
                  </h3>
                  <p className="text-xs text-slate-400">
                    O próprio empresário pode subir a logo e fotos da fachada para destacar seu negócio.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Upload do Logotipo */}
                <div className="p-4 rounded-xl bg-[#070b0e] border border-[#182836] space-y-3">
                  <span className="text-xs font-bold text-slate-300 block">Logotipo da Empresa</span>
                  <div className="flex items-center gap-4">
                    <div className="w-20 h-20 rounded-2xl bg-[#0d151c] border border-[#182836] overflow-hidden flex items-center justify-center shrink-0">
                      {logoUrl ? (
                        <img src={logoUrl} alt="Logo" className="w-full h-full object-cover" />
                      ) : (
                        <Building2 className="w-8 h-8 text-slate-600" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <input
                        ref={logoInputRef}
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                        onChange={(e) => handleUploadImage('logo', e)}
                      />
                      <button
                        type="button"
                        disabled={uploadingLogo}
                        onClick={() => logoInputRef.current?.click()}
                        className="px-3.5 py-2 rounded-xl bg-[#182836] hover:bg-[#253d52] text-xs font-semibold text-white flex items-center gap-2 transition-colors disabled:opacity-50"
                      >
                        {uploadingLogo ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5 text-amber-400" />}
                        {uploadingLogo ? 'Enviando...' : logoUrl ? 'Trocar Logotipo' : 'Enviar Logotipo'}
                      </button>
                      <p className="text-[11px] text-slate-500">PNG, JPG ou WEBP até 5MB.</p>
                    </div>
                  </div>
                </div>

                {/* Upload da Foto de Capa / Banner */}
                <div className="p-4 rounded-xl bg-[#070b0e] border border-[#182836] space-y-3">
                  <span className="text-xs font-bold text-slate-300 block">Foto de Capa / Fachada</span>
                  <div className="space-y-3">
                    <div className="w-full h-20 rounded-xl bg-[#0d151c] border border-[#182836] overflow-hidden flex items-center justify-center">
                      {bannerUrl ? (
                        <img src={bannerUrl} alt="Banner" className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-xs text-slate-600 flex items-center gap-1.5">
                          <ImageIcon className="w-4 h-4" /> Nenhuma capa adicionada
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <input
                        ref={bannerInputRef}
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                        onChange={(e) => handleUploadImage('banner', e)}
                      />
                      <button
                        type="button"
                        disabled={uploadingBanner}
                        onClick={() => bannerInputRef.current?.click()}
                        className="px-3.5 py-2 rounded-xl bg-[#182836] hover:bg-[#253d52] text-xs font-semibold text-white flex items-center gap-2 transition-colors disabled:opacity-50"
                      >
                        {uploadingBanner ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5 text-amber-400" />}
                        {uploadingBanner ? 'Enviando...' : bannerUrl ? 'Trocar Foto de Capa' : 'Enviar Foto de Capa'}
                      </button>
                      <p className="text-[11px] text-slate-500">Formato horizontal recomendado.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Grid de Métricas de Conversão */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-[#0d151c] border border-emerald-900/50 space-y-1 shadow-md">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Contatos pelo WhatsApp</span>
                  <MessageCircle className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-3xl font-black text-emerald-400">Ativo</p>
                <span className="text-[11px] text-emerald-500/80 font-medium">Link direto criptografado</span>
              </div>

              <div className="p-5 rounded-2xl bg-[#0d151c] border border-blue-900/50 space-y-1 shadow-md">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Métodos de Atendimento</span>
                  <Phone className="w-4 h-4 text-blue-400" />
                </div>
                <p className="text-sm font-bold text-blue-400 truncate">
                  {[
                    servesAtLocation && 'No Local',
                    servesAtCustomer && 'A Domicílio',
                    servesOnline && 'Online',
                  ].filter(Boolean).join(' • ') || 'A Definir'}
                </p>
                <span className="text-[11px] text-blue-500/80 font-medium">
                  {servesAtCustomer ? `Raio a domicílio: ${serviceRadiusKm} km` : 'Multi-atendimento ativo'}
                </span>
              </div>

              <div className="p-5 rounded-2xl bg-[#0d151c] border border-amber-900/50 space-y-1 shadow-md">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Verificação de Titularidade</span>
                  <Eye className="w-4 h-4 text-amber-400" />
                </div>
                <p className="text-2xl font-black text-amber-400">
                  {activeBusiness.is_verified ? 'Verificado' : 'Em Análise'}
                </p>
                <span className="text-[11px] text-amber-500/80 font-medium">Selo de confiabilidade</span>
              </div>

              <div className="p-5 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1 shadow-md">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Status do Cadastro</span>
                  <TrendingUp className="w-4 h-4 text-amber-300" />
                </div>
                <p className="text-xl font-bold text-white uppercase">
                  {currentStatus}
                </p>
                <span className="text-[11px] text-slate-400 font-medium">Base PostgreSQL PostGIS</span>
              </div>
            </div>

            {/* Formulário de Edição do Perfil da Empresa */}
            <div className="p-6 md:p-8 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-6 shadow-xl">
              <div className="pb-4 border-b border-[#182836]">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-amber-400" />
                  Editar Informações da Empresa
                </h3>
                <p className="text-xs text-slate-400">
                  Mantenha suas especialidades, canais de contato e localização sempre atualizados.
                </p>
              </div>

              {/* Alerta de Segurança e Curadoria */}
              <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-300 text-xs space-y-1.5 leading-relaxed">
                <div className="flex items-center gap-2 font-bold text-amber-400">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  <span>Regra de Curadoria e Proteção ao Consumidor:</span>
                </div>
                <p>
                  Você pode editar <strong>descrição, fotos, instagram e website</strong> livremente a qualquer momento.
                  Alterações em <strong>WhatsApp ou Endereço físico</strong> reabrem automaticamente a
                  análise na triagem administrativa para garantir a veracidade perante os consumidores.
                </p>
              </div>

              <form onSubmit={handleSaveProfile} className="space-y-5 text-xs">
                {/* Seção 1: Descrição e Canais (Livre) */}
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Star className="w-3.5 h-3.5 text-amber-400" />
                    Apresentação e Diferenciais
                  </h4>

                  <div>
                    <label className="block text-slate-300 font-semibold mb-1">Descrição e Diferenciais do Negócio *</label>
                    <textarea
                      required
                      rows={4}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Descreva seus produtos, serviços, diferenciais, formas de pagamento e garantias..."
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none leading-relaxed"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Telefone Fixo / Adicional</label>
                      <input
                        type="text"
                        placeholder="(19) 3333-2222"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Instagram (@usuario)</label>
                      <input
                        type="text"
                        placeholder="@suaempresa"
                        value={instagram}
                        onChange={(e) => setInstagram(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Website Oficial</label>
                      <input
                        type="text"
                        placeholder="https://suaempresa.com.br"
                        value={website}
                        onChange={(e) => setWebsite(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                      />
                    </div>
                  </div>
                </div>

                {/* Seção 2: Atendimento e Raio Multi-Canal */}
                <div className="space-y-3 pt-4 border-t border-[#182836]">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-amber-400" />
                      Métodos de Atendimento *
                    </h4>
                    <span className="text-[11px] text-amber-400 font-medium">
                      (Marque todas as formas que você atende)
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {/* No Estabelecimento */}
                    <label
                      className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        servesAtLocation
                          ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                          : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={servesAtLocation}
                        onChange={(e) => setServesAtLocation(e.target.checked)}
                        className="mt-0.5 accent-amber-500 w-4 h-4 rounded cursor-pointer"
                      />
                      <div className="text-xs leading-tight">
                        <span className="font-semibold block text-slate-100 flex items-center gap-1">
                          <Store className="w-3.5 h-3.5 text-blue-400 inline" /> No Estabelecimento
                        </span>
                        <span className="text-[11px] text-slate-400 mt-0.5 block">
                          Loja física / balcão próprio
                        </span>
                      </div>
                    </label>

                    {/* A Domicílio */}
                    <label
                      className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        servesAtCustomer
                          ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                          : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={servesAtCustomer}
                        onChange={(e) => setServesAtCustomer(e.target.checked)}
                        className="mt-0.5 accent-amber-500 w-4 h-4 rounded cursor-pointer"
                      />
                      <div className="text-xs leading-tight">
                        <span className="font-semibold block text-slate-100 flex items-center gap-1">
                          <Navigation className="w-3.5 h-3.5 text-emerald-400 inline" /> A Domicílio
                        </span>
                        <span className="text-[11px] text-slate-400 mt-0.5 block">
                          Vou até a casa/empresa do cliente
                        </span>
                      </div>
                    </label>

                    {/* 100% Online */}
                    <label
                      className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        servesOnline
                          ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                          : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={servesOnline}
                        onChange={(e) => setServesOnline(e.target.checked)}
                        className="mt-0.5 accent-amber-500 w-4 h-4 rounded cursor-pointer"
                      />
                      <div className="text-xs leading-tight">
                        <span className="font-semibold block text-slate-100 flex items-center gap-1">
                          <Globe className="w-3.5 h-3.5 text-amber-400 inline" /> Online / Nacional
                        </span>
                        <span className="text-[11px] text-slate-400 mt-0.5 block">
                          Atendimento remoto / todo o Brasil
                        </span>
                      </div>
                    </label>
                  </div>

                  {/* Se atende a domicílio, exibe campo para configurar o raio de deslocamento */}
                  {servesAtCustomer && (
                    <div className="p-3 rounded-xl bg-[#091118] border border-emerald-800/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <div>
                        <span className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                          <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                          Raio Atendido a Domicílio
                        </span>
                        <p className="text-[11px] text-slate-400">
                          Distância máxima em quilômetros atendida a partir do seu endereço
                        </p>
                      </div>
                      <div className="flex items-center gap-2 self-start sm:self-auto">
                        <input
                          type="number"
                          min={1}
                          max={500}
                          value={serviceRadiusKm}
                          onChange={(e) => setServiceRadiusKm(Number(e.target.value))}
                          className="w-24 px-3 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none text-sm text-center font-bold"
                        />
                        <span className="text-xs text-slate-300 font-medium">km</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Seção 3: Campos Sensíveis (Reabrem Triagem) */}
                <div className="space-y-4 pt-4 border-t border-[#182836]">
                  <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-amber-400" />
                    Dados Cadastrais Críticos (Requerem Nova Triagem se Alterados)
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1 flex items-center justify-between">
                        <span>WhatsApp de Atendimento *</span>
                        <span className="text-[10px] text-amber-400 font-mono">Sensível</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={whatsapp}
                        onChange={(e) => setWhatsapp(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1 flex items-center justify-between">
                        <span>Cidade *</span>
                        <span className="text-[10px] text-amber-400 font-mono">Sensível</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1 flex items-center justify-between">
                        <span>Bairro / Região *</span>
                        <span className="text-[10px] text-amber-400 font-mono">Sensível</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={neighborhood}
                        onChange={(e) => setNeighborhood(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={saveLoading}
                    className="w-full sm:w-auto px-8 py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-black text-xs md:text-sm transition-all shadow-lg shadow-amber-950/50 flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {saveLoading ? <Loader2 className="w-4 h-4 animate-spin text-black" /> : <Save className="w-4 h-4 fill-black" />}
                    {saveLoading ? 'Salvando Alterações...' : 'Salvar Alterações do Perfil'}
                  </button>
                </div>
              </form>
            </div>
          </>
        ) : null}
      </main>

      {/* Modal da Carta de Princípios e Valores da Liberdade */}
      <ManifestoModal
        isOpen={showManifestoModal}
        onClose={() => setShowManifestoModal(false)}
      />
    </div>
  );
}
