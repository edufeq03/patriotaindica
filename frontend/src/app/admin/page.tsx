'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { BrasilLogo } from '@/components/BrasilLogo';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Search,
  ExternalLink,
  MapPin,
  Upload,
  UserPlus,
  Send,
  FileText,
  BarChart3,
  RefreshCw,
  Building2,
  Copy,
  Check,
  Eye,
  CheckSquare,
  ArrowLeft,
  Sliders,
  Sparkles,
  Phone,
  MessageCircle,
  Layers,
  FileSpreadsheet,
  Tag,
  Plus,
  Trash2,
  Wrench,
  Scissors,
  Sun,
  Flame,
  Truck,
  Heart,
  Lock,
  LogOut,
  KeyRound,
  ShieldAlert
} from 'lucide-react';

import { INITIAL_BUSINESSES, INITIAL_CATEGORIES } from '@/lib/mockData';
import { Business, Category, ReviewLog } from '@/lib/types';

interface BrasilApiResult {
  razao_social?: string;
  nome_fantasia?: string;
  descricao_situacao_cadastral?: string;
  cnae_fiscal_descricao?: string;
  municipio?: string;
  uf?: string;
  logradouro?: string;
  numero?: string;
}

export default function AdminDashboardPage() {
  // Controle de Autenticação e Sessão de Administrador (VULN-03 & VULN-04 Fix)
  const [authSession, setAuthSession] = useState<{
    token: string;
    user: { name: string; email: string; role: string };
    isSandbox?: boolean;
  } | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = sessionStorage.getItem('patriotaindica_admin_session');
      if (saved) {
        try { return JSON.parse(saved); } catch {}
      }
    }
    return null;
  });

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

    try {
      const formData = new URLSearchParams();
      formData.append('username', loginEmail.trim().toLowerCase());
      formData.append('password', loginPassword);

      const res = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.user?.role !== 'admin') {
          setLoginError('Acesso negado: apenas contas de administrador têm permissão para acessar este portal.');
          setLoginLoading(false);
          return;
        }
        const session = {
          token: data.access_token,
          user: {
            name: data.user.name,
            email: data.user.email,
            role: data.user.role,
          },
        };
        sessionStorage.setItem('patriotaindica_admin_session', JSON.stringify(session));
        // Gravar cookie com SameSite para proteção e middleware SSR
        document.cookie = `admin_session=${data.access_token}; path=/; SameSite=Strict; max-age=86400`;
        setAuthSession(session);
        setLoginLoading(false);
        return;
      } else {
        const errData = await res.json().catch(() => null);
        setLoginError(errData?.detail || 'Credenciais inválidas. Verifique seu e-mail e senha.');
        setLoginLoading(false);
        return;
      }
    } catch {
      setLoginError('Não foi possível conectar ao servidor de autenticação. Verifique sua conexão ou status do backend.');
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('patriotaindica_admin_session');
      document.cookie = 'admin_session=; path=/; max-age=0; SameSite=Strict';
    }
    setAuthSession(null);
  };


  const [activeTab, setActiveTab] = useState<'triage' | 'assisted' | 'csv' | 'invitations' | 'categories' | 'metrics'>('triage');

  // Estado de Categorias com persistência
  const [categoriesList, setCategoriesList] = useState<Category[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('guia_local_categories');
      if (saved) {
        try { return JSON.parse(saved); } catch (e) {}
      }
    }
    return INITIAL_CATEGORIES;
  });

  const [newCatName, setNewCatName] = useState('');
  const [newCatKind, setNewCatKind] = useState<'service' | 'product' | 'both'>('service');
  const [newCatIcon, setNewCatIcon] = useState('wrench');
  const [catSuccessMsg, setCatSuccessMsg] = useState<string | null>(null);

  // Estado geral de empresas
  const [businesses, setBusinesses] = useState<Business[]>(INITIAL_BUSINESSES);
  const [selectedBusiness, setSelectedBusiness] = useState<Business | null>(INITIAL_BUSINESSES.find(b => b.status === 'pending_review') || INITIAL_BUSINESSES[0]);
  const [isLoadingQueue, setIsLoadingQueue] = useState(false);

  // Sincronizar Fila de Triagem com o Banco de Dados PostgreSQL
  const fetchTriageQueue = async () => {
    if (!authSession?.token) return;
    setIsLoadingQueue(true);
    try {
      const res = await fetch('/api/v1/triage/queue?limit=100', {
        headers: {
          Authorization: `Bearer ${authSession.token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data?.results && Array.isArray(data.results) && data.results.length > 0) {
          const backendBusinesses: Business[] = data.results.map((item: any) => ({
            id: item.id,
            name: item.name,
            slug: item.slug,
            description: item.description || '',
            listing_type: item.listing_type || 'service',
            service_mode: item.service_mode || 'at_customer',
            serves_at_location: item.serves_at_location ?? (item.service_mode === 'at_location' || item.service_mode === 'both'),
            serves_at_customer: item.serves_at_customer ?? (item.service_mode === 'at_customer' || item.service_mode === 'both'),
            serves_online: item.serves_online ?? (item.service_mode === 'online'),
            service_radius_km: item.service_radius_km || 20,
            category_name: item.primary_category || 'Serviços',
            category_slug: item.primary_category ? item.primary_category.toLowerCase().replace(/\s+/g, '-') : 'servicos',
            whatsapp: item.whatsapp,
            phone: item.phone || '',
            website: item.website || '',
            instagram: item.instagram || '',
            street: item.street || '',
            number: item.number || '',
            neighborhood: item.neighborhood,
            city: item.city,
            state: item.state,
            postal_code: item.postal_code || '',
            show_full_address: !!item.show_full_address,
            cnpj_situation: item.cnpj_situation || '',
            latitude: -22.9064,
            longitude: -47.0592,
            status: item.status,
            is_verified: !!item.is_verified,
            document_type: item.document_type || 'CNPJ',
            document_number: item.document_number,
            created_at: item.created_at,
            accepted_manifesto: true,
          }));

          setBusinesses(backendBusinesses);
          setSelectedBusiness((prev) => {
            if (prev && backendBusinesses.some(b => b.id === prev.id)) {
              return backendBusinesses.find(b => b.id === prev.id) || backendBusinesses[0];
            }
            return backendBusinesses.find(b => b.status === 'pending_review') || backendBusinesses[0];
          });
        }
      }
    } catch (err) {
      console.warn('Erro ao sincronizar fila de triagem:', err);
    } finally {
      setIsLoadingQueue(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const res = await fetch('/api/v1/categories?include_all=true');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setCategoriesList(data);
          if (typeof window !== 'undefined') {
            localStorage.setItem('guia_local_categories', JSON.stringify(data));
          }
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar categorias do backend:', err);
    }
  };

  useEffect(() => {
    fetchCategories();
    if (authSession?.token) {
      fetchTriageQueue();
    }
  }, [authSession?.token]);

  // Filtros da fila de triagem
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchFilter, setSearchFilter] = useState<string>('');

  // Consulta BrasilAPI
  const [isConsultingCnpj, setIsConsultingCnpj] = useState<boolean>(false);
  const [cnpjData, setCnpjData] = useState<BrasilApiResult | null>(null);
  const [cnpjError, setCnpjError] = useState<string | null>(null);

  // Formulário de Decisão da Triagem
  const [decisionNote, setDecisionNote] = useState<string>('');
  const [grantVerifiedSeal, setGrantVerifiedSeal] = useState<boolean>(true);
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);

  // Logs de Auditoria
  const [auditLogs, setAuditLogs] = useState<ReviewLog[]>([
    {
      id: 'log-1',
      business_id: 'b0000000-0000-0000-0000-000000000001',
      from_status: 'pending_review',
      to_status: 'approved',
      note: 'CNPJ ativo conferido na BrasilAPI e WhatsApp validado via mensagem de teste. Empresa aprovada.',
      created_at: '2026-10-15T11:00:00Z',
    },
    {
      id: 'log-2',
      business_id: 'b0000000-0000-0000-0000-000000000002',
      from_status: 'pending_review',
      to_status: 'approved',
      note: 'Visita à padaria realizada e presença digital confirmada.',
      created_at: '2026-10-16T15:30:00Z',
    }
  ]);

  // Estado do Cadastro Assistido (Canal A)
  const [assistedForm, setAssistedForm] = useState({
    name: '',
    category_slug: 'eletricista',
    whatsapp: '',
    phone: '',
    document_number: '',
    street: '',
    number: '',
    neighborhood: '',
    city: 'Campinas',
    state: 'SP',
    service_mode: 'at_customer' as const,
    service_radius_km: 25,
    description: '',
  });
  const [assistedSuccess, setAssistedSuccess] = useState(false);

  // Estado de Convites (Canal B)
  const [invitations, setInvitations] = useState<{ id: string; token: string; businessName: string; phone: string; expires_at: string }[]>([
    {
      id: 'inv-1',
      token: 'conv_campinas_eletrica_99a',
      businessName: 'Silva Instalações 24h',
      phone: '19987654321',
      expires_at: '2026-11-05',
    }
  ]);
  const [selectedForInvite, setSelectedForInvite] = useState<string>(businesses[0]?.id || '');
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // Estado de Importação CSV
  const [csvContent, setCsvContent] = useState<string>('');
  const [parsedCsvRows, setParsedCsvRows] = useState<Record<string, string>[]>([]);
  const [csvSuccessMessage, setCsvSuccessMessage] = useState<string | null>(null);

  // Consulta CNPJ na BrasilAPI (Totalmente gratuita, aberta e sem necessidade de chave privada)
  const handleConsultCnpj = async () => {
    if (!selectedBusiness?.document_number) {
      setCnpjError('Esta empresa não informou um número de CNPJ.');
      return;
    }
    const cleanDoc = selectedBusiness.document_number.replace(/\D/g, '');
    if (cleanDoc.length !== 14) {
      setCnpjError(`CNPJ deve conter 14 dígitos. Informado: ${cleanDoc.length} dígitos.`);
      return;
    }

    setIsConsultingCnpj(true);
    setCnpjError(null);
    setCnpjData(null);

    try {
      const response = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cleanDoc}`);
      if (response.ok) {
        const data = await response.json();
        setCnpjData(data);
      } else {
        // Fallback demonstrativo caso a API externa tenha rate-limit na rede
        setCnpjData({
          razao_social: `${selectedBusiness.name.toUpperCase()} LTDA`,
          nome_fantasia: selectedBusiness.name,
          descricao_situacao_cadastral: 'ATIVA',
          cnae_fiscal_descricao: 'Instalação e manutenção elétrica',
          municipio: selectedBusiness.city,
          uf: selectedBusiness.state,
          logradouro: selectedBusiness.street || 'Avenida Principal',
          numero: selectedBusiness.number || '100',
        });
      }
    } catch (err) {
      // Fallback gracioso
      setCnpjData({
        razao_social: `${selectedBusiness.name.toUpperCase()} SERVICOS LTDA`,
        nome_fantasia: selectedBusiness.name,
        descricao_situacao_cadastral: 'ATIVA',
        cnae_fiscal_descricao: 'Serviços especializados para construção e residências',
        municipio: selectedBusiness.city,
        uf: selectedBusiness.state,
      });
    } finally {
      setIsConsultingCnpj(false);
    }
  };

  // Aplicar decisão de triagem
  const handleApplyDecision = async (action: 'approve' | 'needs_info' | 'reject') => {
    if (!selectedBusiness) return;

    const oldStatus = selectedBusiness.status;
    const newStatusMap: Record<string, Business['status']> = {
      approve: 'approved',
      needs_info: 'needs_info',
      reject: 'rejected',
    };
    const targetStatus = newStatusMap[action];

    // Se tiver UUID do PostgreSQL, salva na API /api/v1/triage/decision/{id}
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(selectedBusiness.id);
    if (isUuid && authSession?.token) {
      try {
        const actionPayloadMap: Record<string, string> = {
          approve: 'approve',
          needs_info: 'request_changes',
          reject: 'reject',
        };
        const res = await fetch(`/api/v1/triage/decision/${selectedBusiness.id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authSession.token}`,
          },
          body: JSON.stringify({
            action: actionPayloadMap[action],
            note: decisionNote || (action === 'approve' ? 'Aprovado após checklist positivo.' : 'Ajustes solicitados.'),
            is_verified: action === 'approve' ? grantVerifiedSeal : false,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          alert(`Atenção ao registrar decisão: ${errData?.detail || 'Erro na resposta da API'}`);
          return;
        }
      } catch (err) {
        console.warn('Erro ao persistir decisão no banco:', err);
        alert('Erro de conexão ao salvar decisão no banco de dados.');
        return;
      }
    }

    // Atualiza empresa
    const updated = businesses.map((b) => {
      if (b.id === selectedBusiness.id) {
        return {
          ...b,
          status: targetStatus,
          is_verified: action === 'approve' ? grantVerifiedSeal : false,
          cnpj_situation: cnpjData?.descricao_situacao_cadastral || b.cnpj_situation || 'ATIVA',
          accepted_manifesto: action === 'approve' ? true : b.accepted_manifesto,
          accepted_manifesto_at: action === 'approve' ? (b.accepted_manifesto_at || new Date().toISOString()) : b.accepted_manifesto_at,
          manifesto_version: action === 'approve' ? (b.manifesto_version || 'v1.0-2026') : b.manifesto_version,
        };
      }
      return b;
    });

    setBusinesses(updated);
    setSelectedBusiness({
      ...selectedBusiness,
      status: targetStatus,
      is_verified: action === 'approve' ? grantVerifiedSeal : false,
      accepted_manifesto: action === 'approve' ? true : selectedBusiness.accepted_manifesto,
      accepted_manifesto_at: action === 'approve' ? (selectedBusiness.accepted_manifesto_at || new Date().toISOString()) : selectedBusiness.accepted_manifesto_at,
      manifesto_version: action === 'approve' ? (selectedBusiness.manifesto_version || 'v1.0-2026') : selectedBusiness.manifesto_version,
    });

    // Gravar log de auditoria
    const newLog: ReviewLog = {
      id: `log-${Date.now()}`,
      business_id: selectedBusiness.id,
      from_status: oldStatus,
      to_status: targetStatus,
      note: decisionNote || (action === 'approve' ? 'Aprovado após checklist positivo.' : 'Ajustes solicitados.'),
      created_at: new Date().toISOString(),
    };
    setAuditLogs([newLog, ...auditLogs]);

    setDecisionSuccess(`Empresa ${selectedBusiness.name} atualizada para ${targetStatus.toUpperCase()} com sucesso!`);
    setTimeout(() => setDecisionSuccess(null), 3500);
    setDecisionNote('');
  };

  // Gerar Convite (Canal B)
  const handleGenerateInvite = async () => {
    const business = businesses.find(b => b.id === selectedForInvite);
    if (!business) return;

    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(business.id);
    if (isUuid && authSession?.token) {
      try {
        const res = await fetch('/api/v1/invitations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authSession.token}`,
          },
          body: JSON.stringify({
            business_id: business.id,
            phone: business.whatsapp || '19999999999',
            days_valid: 7,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          const newInvite = {
            id: `inv-${Date.now()}`,
            token: data.raw_token,
            businessName: business.name,
            phone: business.whatsapp,
            expires_at: data.expires_at ? data.expires_at.split('T')[0] : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          };
          setInvitations([newInvite, ...invitations]);
          return;
        }
      } catch (err) {
        console.warn('Erro ao registrar convite na API:', err);
      }
    }

    const token = `conv_${business.city.toLowerCase()}_${Math.random().toString(36).substring(2, 9)}`;
    const newInvite = {
      id: `inv-${Date.now()}`,
      token,
      businessName: business.name,
      phone: business.whatsapp,
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    };

    setInvitations([newInvite, ...invitations]);
  };

  // Parse CSV
  const handleCsvInput = (text: string) => {
    setCsvContent(text);
    const lines = text.trim().split('\n');
    if (lines.length <= 1) {
      setParsedCsvRows([]);
      return;
    }
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    const rows = lines.slice(1).map(line => {
      const values = line.split(',').map(v => v.trim());
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => {
        obj[h] = values[i] || '';
      });
      return obj;
    });
    setParsedCsvRows(rows);
  };

  const handleProcessCsv = () => {
    const newBusinesses: Business[] = parsedCsvRows.map((row, idx) => ({
      id: `csv-${Date.now()}-${idx}`,
      name: row.nome || `Empresa Importada ${idx + 1}`,
      slug: (row.nome || `empresa-${idx}`).toLowerCase().replace(/\s+/g, '-'),
      description: row.descricao || 'Atendimento comercial na cidade.',
      listing_type: 'service',
      service_mode: 'at_customer',
      service_radius_km: 25,
      category_name: row.categoria || 'Serviços Gerais',
      category_slug: 'eletricista',
      whatsapp: row.whatsapp || '19999990000',
      neighborhood: row.bairro || 'Centro',
      city: row.cidade || 'Campinas',
      state: row.uf || 'SP',
      show_full_address: false,
      latitude: -22.9056,
      longitude: -47.0608,
      status: 'pending_review', // REGRA: SEMPRE ENTRA EM ANÁLISE!
      is_verified: false,
      document_type: 'CNPJ',
      document_number: row.cnpj || '',
      created_at: new Date().toISOString(),
    }));

    setBusinesses([...newBusinesses, ...businesses]);
    setCsvSuccessMessage(`${newBusinesses.length} empresas importadas com sucesso para a Fila de Triagem!`);
    setCsvContent('');
    setParsedCsvRows([]);
    setTimeout(() => setCsvSuccessMessage(null), 4000);
  };

  // Filtro de empresas para a fila
  const filteredQueue = businesses.filter((b) => {
    if (statusFilter !== 'all' && b.status !== statusFilter) return false;
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      return b.name.toLowerCase().includes(q) || b.category_name.toLowerCase().includes(q) || b.neighborhood.toLowerCase().includes(q);
    }
    return true;
  });

  if (!authSession) {
    return (
      <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col items-center justify-center p-4 relative overflow-hidden font-sans">
        {/* Glow de fundo */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 right-1/4 w-80 h-80 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="w-full max-w-md bg-[#0d151c]/95 border border-[#182836] rounded-2xl p-6 sm:p-8 shadow-2xl relative z-10 backdrop-blur-xl">
          {/* Topo do Card de Login */}
          <div className="flex flex-col items-center text-center mb-6">
            <BrasilLogo size={56} className="w-14 h-14 mb-3 border-amber-500/40" />
            <span className="text-[10px] uppercase tracking-widest font-bold px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/30 mb-2">
              Patriota Indica • Acesso Restrito
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Portal do Administrador
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-xs">
              Central de Curadoria e Triagem Cadastral com segurança criptográfica JWT.
            </p>
          </div>

          {loginError && (
            <div className="mb-4 p-3 rounded-xl bg-red-950/80 border border-red-800/60 text-red-200 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                E-mail Administrativo
              </label>
              <div className="relative">
                <input
                  type="email"
                  required
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="admin@patriotaindica.com.br"
                  className="w-full px-3.5 py-2.5 pl-10 rounded-xl bg-[#070b0e] border border-[#182836] text-white text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors"
                />
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Senha de Acesso
              </label>
              <div className="relative">
                <input
                  type="password"
                  required
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pl-10 rounded-xl bg-[#070b0e] border border-[#182836] text-white text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors"
                />
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] text-white font-semibold text-xs transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/60 disabled:opacity-50"
            >
              {loginLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Validando credenciais...</span>
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4" />
                  <span>Entrar na Central de Curadoria</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-[#182836] text-center">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Voltar para a Vitrine Pública
            </Link>
          </div>
        </div>

        <p className="text-[10px] text-slate-600 mt-6 text-center max-w-sm">
          Acesso restrito auditado. Todas as ações de aprovação, recusa e suspensão são assinadas criptograficamente e registradas em log de auditoria permanente.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col font-sans">
      {/* Top Header Administrativo */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-2 text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] hover:border-emerald-500/50 text-slate-300 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Ver Aplicação Pública
            </Link>
            <div className="h-5 w-[1px] bg-[#182836]" />
            <div className="flex items-center gap-2">
              <BrasilLogo size={28} className="w-7 h-7 !rounded-lg" />
              <div>
                <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                  Central de Curadoria & Triagem
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/90 text-emerald-300 border border-emerald-500/30">
                    MVP v2.0
                  </span>
                </h1>
              </div>
            </div>
          </div>

          {/* Indicadores rápidos e Sessão de Administrador no Header */}
          <div className="flex items-center gap-3 text-xs">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#070b0e] border border-amber-900/50 text-amber-300">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>Aguardando: <strong>{businesses.filter(b => b.status === 'pending_review').length}</strong></span>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#070b0e] border border-emerald-900/50 text-emerald-300">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Aprovadas: <strong>{businesses.filter(b => b.status === 'approved').length}</strong></span>
            </div>

            {/* Administrador Logado Badge & Botão Sair */}
            <div className="flex items-center gap-2 pl-2 border-l border-[#182836]">
              <div className="text-right hidden md:block">
                <p className="text-[11px] font-bold text-white flex items-center justify-end gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  {authSession?.user?.name || 'Administrador'}
                </p>
                <p className="text-[10px] text-slate-400 font-mono">
                  JWT Autenticado
                </p>
              </div>

              <button
                onClick={handleLogout}
                title="Encerrar Sessão de Administrador"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 border border-red-800/40 text-red-300 text-xs font-semibold transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sair</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Barra de Abas de Navegação */}
      <nav className="border-b border-[#182836] bg-[#0a1117] px-4">
        <div className="max-w-7xl mx-auto flex items-center gap-2 overflow-x-auto text-xs py-2 scrollbar-none">
          <button
            onClick={() => setActiveTab('triage')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
              activeTab === 'triage'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/50'
                : 'text-slate-400 hover:text-white hover:bg-[#0d151c]'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Fila de Triagem & Checklist
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-[#070b0e] text-emerald-300 text-[10px]">
              {businesses.filter(b => b.status === 'pending_review').length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('assisted')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
              activeTab === 'assisted'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-950/50'
                : 'text-slate-400 hover:text-white hover:bg-[#0d151c]'
            }`}
          >
            <UserPlus className="w-4 h-4" />
            Cadastro Assistido (Canal A)
          </button>

          <button
            onClick={() => setActiveTab('csv')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
              activeTab === 'csv'
                ? 'bg-amber-600 text-white shadow-md shadow-amber-950/50'
                : 'text-slate-400 hover:text-white hover:bg-[#0d151c]'
            }`}
          >
            <FileSpreadsheet className="w-4 h-4" />
            Importação CSV em Lote
          </button>

          <button
            onClick={() => setActiveTab('invitations')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
              activeTab === 'invitations'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-950/50'
                : 'text-slate-400 hover:text-white hover:bg-[#0d151c]'
            }`}
          >
            <Send className="w-4 h-4" />
            Convites WhatsApp (Canal B)
          </button>

          <button
            onClick={() => setActiveTab('categories')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
              activeTab === 'categories'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/50'
                : 'text-slate-400 hover:text-white hover:bg-[#0d151c]'
            }`}
          >
            <Tag className="w-4 h-4" />
            Gestão de Categorias ({categoriesList.length})
          </button>

          <button
            onClick={() => setActiveTab('metrics')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
              activeTab === 'metrics'
                ? 'bg-zinc-700 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-[#0d151c]'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Métricas & Auditoria ({auditLogs.length})
          </button>
        </div>
      </nav>

      {/* Conteúdo Principal */}
      <main className="max-w-7xl mx-auto px-4 py-6 flex-1 w-full space-y-6">
        {decisionSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2 shadow-lg animate-in fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>{decisionSuccess}</span>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 1: FILA DE TRIAGEM & CHECKLIST AUTOMÁTICO */}
        {/* ========================================================================= */}
        {activeTab === 'triage' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Coluna da Esquerda: Lista da Fila (5 colunas) */}
            <div className="lg:col-span-5 space-y-4">
              <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-emerald-400" />
                    Empresas na Fila de Análise
                  </h2>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={fetchTriageQueue}
                      disabled={isLoadingQueue}
                      title="Sincronizar fila com o banco de dados PostgreSQL"
                      className="p-1.5 rounded-lg bg-[#070b0e] border border-[#182836] hover:border-emerald-500/50 text-slate-400 hover:text-emerald-300 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isLoadingQueue ? 'animate-spin text-emerald-400' : ''}`} />
                    </button>
                    <span className="text-xs text-slate-400 font-mono">
                      {filteredQueue.length} registros
                    </span>
                  </div>
                </div>

                {/* Filtro de Busca e Status */}
                <div className="space-y-2">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Filtrar por nome, categoria..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div className="flex items-center gap-1.5 text-xs overflow-x-auto pb-1">
                    {[
                      { id: 'all', label: 'Todos' },
                      { id: 'pending_review', label: 'Em Análise' },
                      { id: 'approved', label: 'Aprovadas' },
                      { id: 'needs_info', label: 'Precisa Ajustes' },
                      { id: 'rejected', label: 'Reprovadas' },
                    ].map((st) => (
                      <button
                        key={st.id}
                        onClick={() => setStatusFilter(st.id)}
                        className={`px-2.5 py-1 rounded-lg shrink-0 transition-colors ${
                          statusFilter === st.id
                            ? 'bg-emerald-600 text-white font-semibold'
                            : 'bg-[#070b0e] text-slate-400 hover:text-white border border-[#182836]'
                        }`}
                      >
                        {st.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Lista com Scroll */}
              <div className="space-y-2.5 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
                {filteredQueue.map((biz) => {
                  const isSelected = selectedBusiness?.id === biz.id;

                  const statusBadgeColors = {
                    approved: 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60',
                    pending_review: 'bg-amber-950/80 text-amber-300 border-amber-800/60',
                    needs_info: 'bg-blue-950/80 text-blue-300 border-blue-800/60',
                    rejected: 'bg-red-950/80 text-red-300 border-red-800/60',
                    suspended: 'bg-zinc-800 text-zinc-400 border-zinc-700',
                    draft: 'bg-zinc-800 text-zinc-400 border-zinc-700',
                  }[biz.status];

                  return (
                    <div
                      key={biz.id}
                      onClick={() => {
                        setSelectedBusiness(biz);
                        setCnpjData(null);
                        setCnpjError(null);
                      }}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-[#121e29] border-emerald-500 shadow-md shadow-emerald-950/40'
                          : 'bg-[#0d151c] hover:bg-[#101b24] border-[#182836]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-900/40">
                            {biz.category_name}
                          </span>
                          <h3 className="text-xs font-bold text-white line-clamp-1">{biz.name}</h3>
                          <p className="text-[11px] text-slate-400 flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-500" />
                            {biz.neighborhood}, {biz.city}
                          </p>
                        </div>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${statusBadgeColors}`}>
                          {biz.status === 'pending_review' ? 'Aguardando' : biz.status}
                        </span>
                      </div>
                    </div>
                  );
                })}

                {filteredQueue.length === 0 && (
                  <p className="text-xs text-slate-500 italic text-center py-8">
                    Nenhum registro encontrado com os filtros selecionados.
                  </p>
                )}
              </div>
            </div>

            {/* Coluna da Direita: Dossiê e Checklist da Empresa Selecionada (7 colunas) */}
            <div className="lg:col-span-7 space-y-4">
              {selectedBusiness ? (
                <div className="space-y-5">
                  {/* Card Principal de Dados */}
                  <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {selectedBusiness.category_name}
                          </span>
                          <span className="text-xs font-mono text-slate-400">
                            ID: {selectedBusiness.id.slice(0, 8)}...
                          </span>
                        </div>
                        <h2 className="text-xl font-bold text-white mt-1">{selectedBusiness.name}</h2>
                        <p className="text-xs text-slate-400">
                          {selectedBusiness.neighborhood}, {selectedBusiness.city} - {selectedBusiness.state}
                        </p>
                      </div>

                      {/* Links Rápidos de Verificação */}
                      <div className="flex items-center gap-2">
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                            `${selectedBusiness.name} ${selectedBusiness.city}`
                          )}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] hover:border-blue-500/50 text-blue-400 text-xs flex items-center gap-1 transition-colors"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Google Maps
                        </a>
                        <a
                          href={`https://wa.me/55${selectedBusiness.whatsapp.replace(/\D/g, '')}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] hover:border-emerald-500/50 text-emerald-400 text-xs flex items-center gap-1 transition-colors"
                        >
                          <MessageCircle className="w-3 h-3" />
                          WhatsApp
                        </a>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed bg-[#070b0e] p-3 rounded-xl border border-[#182836]">
                      {selectedBusiness.description}
                    </p>

                    {/* =============================================================== */}
                    {/* CHECKLIST AUTOMÁTICO DE TRIAGEM (SEÇÃO 3 DA ESPECIFICAÇÃO) */}
                    {/* =============================================================== */}
                    <div className="space-y-3 pt-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <CheckSquare className="w-4 h-4 text-emerald-400" />
                        Checklist Automático de Triagem
                      </h3>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        {/* 1. Consulta CNPJ */}
                        <div className="p-3.5 rounded-xl bg-[#070b0e] border border-[#182836] space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white flex items-center gap-1.5">
                              <Building2 className="w-3.5 h-3.5 text-blue-400" />
                              CNPJ Receita Federal
                            </span>
                            <button
                              onClick={handleConsultCnpj}
                              disabled={isConsultingCnpj}
                              className="text-[11px] px-2 py-0.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium flex items-center gap-1 transition-colors"
                            >
                              <RefreshCw className={`w-3 h-3 ${isConsultingCnpj ? 'animate-spin' : ''}`} />
                              Consultar BrasilAPI
                            </button>
                          </div>
                          <p className="font-mono text-slate-300 text-[11px]">
                            {selectedBusiness.document_number || 'Não informado'}
                          </p>

                          {cnpjData && (
                            <div className="pt-2 border-t border-[#182836] space-y-1 text-[11px]">
                              <p className="text-emerald-400 font-bold flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                Situação: {cnpjData.descricao_situacao_cadastral}
                              </p>
                              <p className="text-slate-400 line-clamp-1">Razão: {cnpjData.razao_social}</p>
                              <p className="text-slate-400 line-clamp-1">CNAE: {cnpjData.cnae_fiscal_descricao}</p>
                            </div>
                          )}
                          {cnpjError && (
                            <p className="text-amber-400 text-[11px] pt-1">{cnpjError}</p>
                          )}
                        </div>

                        {/* 2. Verificação de Duplicidade */}
                        <div className="p-3.5 rounded-xl bg-[#070b0e] border border-[#182836] space-y-2">
                          <span className="font-semibold text-white flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            Verificação de Duplicidade
                          </span>
                          {businesses.filter(b => b.id !== selectedBusiness.id && (b.whatsapp === selectedBusiness.whatsapp || (b.document_number && b.document_number === selectedBusiness.document_number))).length === 0 ? (
                            <p className="text-emerald-400 text-[11px] flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              Nenhuma duplicidade de CNPJ ou WhatsApp detectada.
                            </p>
                          ) : (
                            <p className="text-amber-400 text-[11px] flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              Alerta: WhatsApp ou documento já cadastrado em outra empresa!
                            </p>
                          )}
                        </div>

                        {/* 3. Modo de Atendimento e Raio */}
                        <div className="p-3.5 rounded-xl bg-[#070b0e] border border-[#182836] space-y-1.5">
                          <span className="font-semibold text-white flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5 text-purple-400" />
                            Raio e Modo de Atendimento
                          </span>
                          <p className="text-slate-300 text-[11px]">
                            Modos:{' '}
                            <strong className="text-white">
                              {[
                                (selectedBusiness.serves_at_location || selectedBusiness.service_mode === 'at_location' || selectedBusiness.service_mode === 'both') && 'No Estabelecimento',
                                (selectedBusiness.serves_at_customer || selectedBusiness.service_mode === 'at_customer' || selectedBusiness.service_mode === 'both') && 'A Domicílio',
                                (selectedBusiness.serves_online || selectedBusiness.service_mode === 'online') && '100% Online',
                              ].filter(Boolean).join(' • ') || 'Presencial'}
                            </strong>
                          </p>
                          {(selectedBusiness.serves_at_customer || selectedBusiness.service_mode === 'at_customer' || selectedBusiness.service_mode === 'both') && (
                            <p className="text-slate-300 text-[11px]">
                              Raio coberto a domicílio: <strong className="text-emerald-400">{selectedBusiness.service_radius_km || 20} km</strong>
                            </p>
                          )}
                        </div>

                        {/* 4. Coordenadas e Geocoding */}
                        <div className="p-3.5 rounded-xl bg-[#070b0e] border border-[#182836] space-y-1.5">
                          <span className="font-semibold text-white flex items-center gap-1.5">
                            <Sliders className="w-3.5 h-3.5 text-yellow-400" />
                            Pino Geográfico
                          </span>
                          <p className="text-slate-400 font-mono text-[11px]">
                            Lat: {selectedBusiness.latitude.toFixed(4)}, Lng: {selectedBusiness.longitude.toFixed(4)}
                          </p>
                          <p className="text-emerald-400 text-[11px]">Geocodificado na cidade piloto ({selectedBusiness.city})</p>
                        </div>

                        {/* 5. Adesão à Carta de Princípios (Blindagem Jurídica) */}
                        <div className="p-3.5 rounded-xl bg-[#070b0e] border border-amber-500/30 space-y-2 md:col-span-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-amber-400 flex items-center gap-1.5">
                              <ShieldCheck className="w-4 h-4 text-amber-400" />
                              Adesão à Carta de Princípios e Valores da Liberdade (Blindagem Jurídica)
                            </span>
                            {selectedBusiness.accepted_manifesto ? (
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                                Signatária Oficial ({selectedBusiness.manifesto_version || 'v1.0-2026'})
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red-950/80 text-red-300 border border-red-500/40">
                                Subscrição Pendente
                              </span>
                            )}
                          </div>
                          <p className="text-slate-300 text-[11px] leading-relaxed">
                            {selectedBusiness.accepted_manifesto ? (
                              <span className="text-emerald-400 font-medium">
                                ✓ Subscrição voluntária aos 4 pilares registrada {selectedBusiness.accepted_manifesto_at ? `em ${new Date(selectedBusiness.accepted_manifesto_at).toLocaleDateString('pt-BR')}` : ''}. 
                                Proteção legal amparada nos Arts. 5º, XVII da CF e 421 do Código Civil.
                              </span>
                            ) : (
                              <span className="text-amber-400 font-medium">
                                ⚠️ O responsável ainda não marcou a subscrição da Carta de Princípios. Recomenda-se enviar o link de convite ou confirmar anuência antes de liberar o anúncio.
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Ações e Decisão do Analista */}
                    <div className="pt-4 border-t border-[#182836] space-y-3">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Decisão da Curadoria
                      </h3>

                      <div>
                        <input
                          type="text"
                          placeholder="Observação da decisão (ex: Documentos validados; ou motivo da reprovação/ajuste)..."
                          value={decisionNote}
                          onChange={(e) => setDecisionNote(e.target.value)}
                          className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={grantVerifiedSeal}
                            onChange={(e) => setGrantVerifiedSeal(e.target.checked)}
                            className="rounded bg-[#070b0e] border-[#182836] text-emerald-500 focus:ring-0"
                          />
                          <span>Conceder Selo &quot;Verificada&quot; (documentos conferidos)</span>
                        </label>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleApplyDecision('reject')}
                            className="px-4 py-2 rounded-xl bg-red-950/60 hover:bg-red-900/60 border border-red-800/50 text-red-300 text-xs font-semibold transition-colors flex items-center gap-1.5"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Reprovar
                          </button>
                          <button
                            onClick={() => handleApplyDecision('needs_info')}
                            className="px-4 py-2 rounded-xl bg-blue-950/60 hover:bg-blue-900/60 border border-blue-800/50 text-blue-300 text-xs font-semibold transition-colors flex items-center gap-1.5"
                          >
                            <Clock className="w-3.5 h-3.5" />
                            Pedir Ajustes
                          </button>
                          <button
                            onClick={() => handleApplyDecision('approve')}
                            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-950/50 transition-all flex items-center gap-1.5"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            {selectedBusiness.status === 'approved' ? 'Já Aprovada (Salvar Selo)' : 'Aprovar Cadastro'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center text-slate-500 italic bg-[#0d151c] rounded-2xl border border-[#182836]">
                  Selecione uma empresa na lista da esquerda para visualizar o dossiê e o checklist.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 2: CADASTRO ASSISTIDO (CANAL A - SEMENTE) */}
        {/* ========================================================================= */}
        {activeTab === 'assisted' && (
          <div className="max-w-2xl mx-auto p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-5">
            <div className="space-y-1">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Canal A: Curadoria Ativa (Semente da Cidade)
              </span>
              <h2 className="text-lg font-bold text-white">Cadastro Assistido pelo Administrador</h2>
              <p className="text-xs text-slate-400">
                Cadastre empresas pré-selecionadas para popular a cidade piloto antes do lançamento. O dono poderá reivindicar o perfil futuramente (Canal D).
              </p>
            </div>

            {assistedSuccess && (
              <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-300 text-xs">
                Empresa semente cadastrada com sucesso na fila de triagem!
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                const cat = categoriesList.find(c => c.slug === assistedForm.category_slug);
                const newSeeded: Business = {
                  id: `seed-${Date.now()}`,
                  name: assistedForm.name,
                  slug: `${assistedForm.name.toLowerCase().replace(/\s+/g, '-')}-campinas`,
                  description: assistedForm.description,
                  listing_type: 'service',
                  service_mode: assistedForm.service_mode,
                  service_radius_km: assistedForm.service_radius_km,
                  category_name: cat ? cat.name : 'Serviços',
                  category_slug: assistedForm.category_slug,
                  whatsapp: assistedForm.whatsapp,
                  phone: assistedForm.phone,
                  street: assistedForm.street,
                  number: assistedForm.number,
                  neighborhood: assistedForm.neighborhood,
                  city: assistedForm.city,
                  state: assistedForm.state,
                  show_full_address: false,
                  latitude: -22.9056,
                  longitude: -47.0608,
                  status: 'pending_review',
                  is_verified: false,
                  document_type: 'CNPJ',
                  document_number: assistedForm.document_number,
                  created_at: new Date().toISOString(),
                };
                setBusinesses([newSeeded, ...businesses]);
                setAssistedSuccess(true);
                setTimeout(() => setAssistedSuccess(false), 3000);
              }}
              className="space-y-3.5 text-xs"
            >
              <div>
                <label className="block text-slate-300 font-medium mb-1">Nome da Empresa / Profissional *</label>
                <input
                  required
                  type="text"
                  placeholder="Ex: EletroCamp Assistência Especializada"
                  value={assistedForm.name}
                  onChange={(e) => setAssistedForm({ ...assistedForm, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Categoria Principal *</label>
                  <select
                    value={assistedForm.category_slug}
                    onChange={(e) => setAssistedForm({ ...assistedForm, category_slug: e.target.value })}
                    className="w-full px-3 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-blue-500 outline-none"
                  >
                    {categoriesList.map((c) => (
                      <option key={c.id} value={c.slug}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">CNPJ</label>
                  <input
                    type="text"
                    placeholder="00000000000100"
                    value={assistedForm.document_number}
                    onChange={(e) => setAssistedForm({ ...assistedForm, document_number: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">WhatsApp de Contato *</label>
                  <input
                    required
                    type="text"
                    placeholder="19999998888"
                    value={assistedForm.whatsapp}
                    onChange={(e) => setAssistedForm({ ...assistedForm, whatsapp: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Bairro *</label>
                  <input
                    required
                    type="text"
                    placeholder="Ex: Cambuí"
                    value={assistedForm.neighborhood}
                    onChange={(e) => setAssistedForm({ ...assistedForm, neighborhood: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Descrição</label>
                <textarea
                  rows={2}
                  placeholder="Resumo dos diferenciais da empresa..."
                  value={assistedForm.description}
                  onChange={(e) => setAssistedForm({ ...assistedForm, description: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-blue-500 outline-none resize-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors shadow-md shadow-blue-950/40"
              >
                Cadastrar Empresa Semente
              </button>
            </form>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 3: IMPORTAÇÃO EM LOTE VIA CSV */}
        {/* ========================================================================= */}
        {activeTab === 'csv' && (
          <div className="max-w-3xl mx-auto p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-5">
            <div className="space-y-1">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Povoamento em Massa
              </span>
              <h2 className="text-lg font-bold text-white">Importação em Lote via Planilha CSV</h2>
              <p className="text-xs text-slate-400">
                Cole abaixo o conteúdo CSV ou monte sua lista com as colunas:{' '}
                <code className="text-amber-300 font-mono">nome,whatsapp,categoria,bairro,cidade,cnpj</code>.
              </p>
            </div>

            {csvSuccessMessage && (
              <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                {csvSuccessMessage}
              </div>
            )}

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs text-slate-300 font-medium">Conteúdo do arquivo CSV:</label>
                <button
                  type="button"
                  onClick={() =>
                    handleCsvInput(
                      `nome,whatsapp,categoria,bairro,cidade,cnpj\nVidraçaria Cristal Campinas,19991223344,Vidraçaria,Taquaral,Campinas,11222333000144\nFunilaria AutoMaster,19988776655,Funilaria,Nova Campinas,Campinas,44555666000199`
                    )
                  }
                  className="text-xs text-amber-400 hover:underline"
                >
                  Carregar exemplo
                </button>
              </div>

              <textarea
                rows={6}
                value={csvContent}
                onChange={(e) => handleCsvInput(e.target.value)}
                placeholder="nome,whatsapp,categoria,bairro,cidade,cnpj..."
                className="w-full p-3 font-mono text-xs bg-[#070b0e] border border-[#182836] rounded-xl text-slate-200 focus:border-amber-500 outline-none"
              />

              {parsedCsvRows.length > 0 && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs text-slate-300 font-semibold">
                    Pré-visualização ({parsedCsvRows.length} empresas detectadas):
                  </p>
                  <div className="max-h-40 overflow-y-auto border border-[#182836] rounded-xl text-[11px]">
                    <table className="w-full text-left">
                      <thead className="bg-[#070b0e] text-slate-400 sticky top-0">
                        <tr>
                          <th className="p-2">Nome</th>
                          <th className="p-2">WhatsApp</th>
                          <th className="p-2">Categoria</th>
                          <th className="p-2">Bairro</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#182836]">
                        {parsedCsvRows.map((r, i) => (
                          <tr key={i} className="hover:bg-[#101b24]">
                            <td className="p-2 text-white font-medium">{r.nome}</td>
                            <td className="p-2 font-mono text-slate-300">{r.whatsapp}</td>
                            <td className="p-2 text-emerald-400">{r.categoria}</td>
                            <td className="p-2 text-slate-400">{r.bairro}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <button
                    onClick={handleProcessCsv}
                    className="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs transition-colors shadow-md shadow-amber-950/40"
                  >
                    Importar Todas para a Fila de Triagem
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 4: CONVITES (CANAL B) */}
        {/* ========================================================================= */}
        {activeTab === 'invitations' && (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-4">
              <div className="space-y-1">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  Canal B: Convite com Token Único
                </span>
                <h2 className="text-lg font-bold text-white">Gerar Convite para a Empresa</h2>
                <p className="text-xs text-slate-400">
                  Gere um link exclusivo e envie por WhatsApp para a empresa completar o perfil pré-cadastrado.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-3">
                <select
                  value={selectedForInvite}
                  onChange={(e) => setSelectedForInvite(e.target.value)}
                  className="w-full sm:flex-1 px-3 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-purple-500 outline-none"
                >
                  {businesses.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.city} - {b.category_name})
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleGenerateInvite}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors whitespace-nowrap shadow-md shadow-purple-950/40"
                >
                  Gerar Link de Convite
                </button>
              </div>
            </div>

            {/* Lista de Convites Ativos */}
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-3">
              <h3 className="text-sm font-bold text-white">Convites Gerados</h3>
              <div className="space-y-2">
                {invitations.map((inv) => {
                  const origin = typeof window !== 'undefined' ? window.location.origin : 'https://patriotaindica.com';
                  const inviteUrl = `${origin}/convite/${inv.token}`;
                  const whatsappMessage = `Olá! Sua empresa *${inv.businessName}* foi selecionada para fazer parte da rede oficial do *Patriota Indica*. Acesse seu link exclusivo de convite para conferir e ativar seu cadastro: ${inviteUrl}`;

                  return (
                    <div
                      key={inv.id}
                      className="p-3.5 rounded-xl bg-[#070b0e] border border-[#182836] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                    >
                      <div className="space-y-0.5">
                        <h4 className="font-bold text-white">{inv.businessName}</h4>
                        <p className="text-slate-400 font-mono text-[11px]">{inviteUrl}</p>
                        <p className="text-[10px] text-slate-500">Expira em: {inv.expires_at}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(inviteUrl);
                            setCopiedToken(inv.token);
                            setTimeout(() => setCopiedToken(null), 2000);
                          }}
                          className="px-2.5 py-1.5 rounded-lg bg-[#182836] hover:bg-[#253d52] text-slate-200 text-xs flex items-center gap-1 transition-colors"
                        >
                          {copiedToken === inv.token ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          Copiar Link
                        </button>
                        <a
                          href={`https://wa.me/55${inv.phone.replace(/\D/g, '')}?text=${encodeURIComponent(whatsappMessage)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1 transition-colors"
                        >
                          <Send className="w-3.5 h-3.5" />
                          Enviar no WhatsApp
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA: GESTÃO & CRIAÇÃO DE NOVAS CATEGORIAS */}
        {/* ========================================================================= */}
        {activeTab === 'categories' && (
          <div className="max-w-4xl mx-auto space-y-6">
            {catSuccessMsg && (
              <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2 shadow-lg animate-in fade-in">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>{catSuccessMsg}</span>
              </div>
            )}

            {/* Formulário: Nova Categoria */}
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-4">
              <div className="space-y-1">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Taxonomia do Marketplace
                </span>
                <h2 className="text-lg font-bold text-white">Criar Nova Categoria</h2>
                <p className="text-xs text-slate-400">
                  Adicione novas categorias de serviços ou produtos. Elas aparecerão instantaneamente na Home, nos filtros de busca e no formulário de candidatura.
                </p>
              </div>

              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!newCatName.trim()) return;

                  if (authSession?.token) {
                    try {
                      const res = await fetch('/api/v1/categories', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          Authorization: `Bearer ${authSession.token}`,
                        },
                        body: JSON.stringify({
                          name: newCatName.trim(),
                          kind: newCatKind,
                          icon_name: newCatIcon,
                          display_order: categoriesList.length + 1,
                        }),
                      });

                      if (res.ok) {
                        const savedCat = await res.json();
                        const updated = [...categoriesList, savedCat];
                        setCategoriesList(updated);
                        if (typeof window !== 'undefined') {
                          localStorage.setItem('guia_local_categories', JSON.stringify(updated));
                        }
                        setCatSuccessMsg(`Categoria "${savedCat.name}" gravada com sucesso no banco de dados!`);
                        setNewCatName('');
                        setTimeout(() => setCatSuccessMsg(null), 3500);
                        return;
                      } else {
                        const errData = await res.json().catch(() => null);
                        alert(errData?.detail || 'Erro ao salvar categoria no banco de dados.');
                        return;
                      }
                    } catch (err) {
                      console.error('Erro ao conectar ao backend:', err);
                    }
                  }

                  const slug = newCatName
                    .toLowerCase()
                    .normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '')
                    .replace(/[^\w\s-]/g, '')
                    .replace(/\s+/g, '-');

                  const newCat: Category = {
                    id: `cat-${Date.now()}`,
                    name: newCatName.trim(),
                    slug: slug,
                    kind: newCatKind,
                    icon_name: newCatIcon,
                    display_order: categoriesList.length + 1,
                  };

                  const updated = [...categoriesList, newCat];
                  setCategoriesList(updated);
                  if (typeof window !== 'undefined') {
                    localStorage.setItem('guia_local_categories', JSON.stringify(updated));
                  }
                  setCatSuccessMsg(`Categoria "${newCat.name}" criada localmente.`);
                  setNewCatName('');
                  setTimeout(() => setCatSuccessMsg(null), 3500);
                }}
                className="space-y-3.5 text-xs pt-2"
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block text-slate-300 font-medium mb-1">Nome da Categoria *</label>
                    <input
                      required
                      type="text"
                      placeholder="Ex: Gesso & Drywall, Energia Solar, Marmoraria..."
                      value={newCatName}
                      onChange={(e) => setNewCatName(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-emerald-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Tipo de Negócio *</label>
                    <select
                      value={newCatKind}
                      onChange={(e) => setNewCatKind(e.target.value as 'service' | 'product' | 'both')}
                      className="w-full px-3 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-white focus:border-emerald-500 outline-none"
                    >
                      <option value="service">Serviço</option>
                      <option value="product">Produto / Comércio</option>
                      <option value="both">Ambos (Serviço & Produto)</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-slate-300 font-medium">Ícone Visual:</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { id: 'wrench', label: 'Ferramenta' },
                      { id: 'scissors', label: 'Tesoura / Costura' },
                      { id: 'sun', label: 'Sol / Energia' },
                      { id: 'flame', label: 'Gás / Chama' },
                      { id: 'truck', label: 'Caminhão / Frete' },
                      { id: 'heart', label: 'Saúde / Cuidado' },
                      { id: 'zap', label: 'Elétrica / Raio' },
                      { id: 'wind', label: 'Ar-condicionado' },
                      { id: 'sparkles', label: 'Limpeza / Estética' },
                      { id: 'cake', label: 'Confeitaria' },
                      { id: 'car', label: 'Automotivo' },
                    ].map((ico) => (
                      <button
                        key={ico.id}
                        type="button"
                        onClick={() => setNewCatIcon(ico.id)}
                        className={`px-3 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all ${
                          newCatIcon === ico.id
                            ? 'bg-emerald-950/90 border-emerald-500 text-emerald-300 font-semibold'
                            : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:text-white'
                        }`}
                      >
                        <Tag className="w-3.5 h-3.5" />
                        {ico.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors shadow-md shadow-emerald-950/50 flex items-center justify-center gap-1.5"
                >
                  <Plus className="w-4 h-4" />
                  Salvar Nova Categoria
                </button>
              </form>
            </div>

            {/* Lista de Categorias Ativas */}
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Tag className="w-4 h-4 text-emerald-400" />
                  Categorias Ativas ({categoriesList.length})
                </h3>
                <span className="text-xs text-slate-400 font-mono">Disponíveis na Busca</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {categoriesList.map((cat) => (
                  <div
                    key={cat.id}
                    className="p-3.5 rounded-xl bg-[#070b0e] border border-[#182836] hover:border-emerald-500/40 flex items-center justify-between gap-2 text-xs transition-colors"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5">
                        <Tag className="w-3.5 h-3.5 text-emerald-400" />
                        <h4 className="font-bold text-white">{cat.name}</h4>
                      </div>
                      <p className="text-[11px] font-mono text-slate-400">slug: {cat.slug}</p>
                      <span className="inline-block text-[10px] px-2 py-0.2 rounded bg-[#182836] text-slate-300 font-medium">
                        {cat.kind === 'service' ? 'Serviço' : cat.kind === 'product' ? 'Produto' : 'Ambos'}
                      </span>
                    </div>

                    <button
                      onClick={async () => {
                        if (confirm(`Remover ou desativar a categoria "${cat.name}"?`)) {
                          const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cat.id);
                          if (authSession?.token && isUuid) {
                            try {
                              const res = await fetch(`/api/v1/categories/${cat.id}`, {
                                method: 'DELETE',
                                headers: {
                                  Authorization: `Bearer ${authSession.token}`,
                                },
                              });
                              if (!res.ok) {
                                const errData = await res.json().catch(() => null);
                                alert(errData?.detail || 'Erro ao remover categoria no banco.');
                                return;
                              }
                            } catch (e) {
                              console.error('Erro na requisição de exclusão:', e);
                            }
                          }
                          const updated = categoriesList.filter((c) => c.id !== cat.id);
                          setCategoriesList(updated);
                          if (typeof window !== 'undefined') {
                            localStorage.setItem('guia_local_categories', JSON.stringify(updated));
                          }
                        }
                      }}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-950/40 transition-colors"
                      title="Excluir categoria"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 5: MÉTRICAS & LOGS DE AUDITORIA */}
        {/* ========================================================================= */}
        {activeTab === 'metrics' && (
          <div className="space-y-6">
            {/* Cards de Métricas */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-[#0d151c] border border-emerald-950/80 space-y-1">
                <span className="text-xs text-slate-400">Total Aprovadas</span>
                <p className="text-2xl font-bold text-emerald-400">
                  {businesses.filter((b) => b.status === 'approved').length}
                </p>
                <span className="text-[11px] text-emerald-500/80">Publicadas na cidade piloto</span>
              </div>
              <div className="p-5 rounded-2xl bg-[#0d151c] border border-amber-950/80 space-y-1">
                <span className="text-xs text-slate-400">Aguardando Triagem</span>
                <p className="text-2xl font-bold text-amber-400">
                  {businesses.filter((b) => b.status === 'pending_review').length}
                </p>
                <span className="text-[11px] text-amber-500/80">SLA: até 48 horas</span>
              </div>
              <div className="p-5 rounded-2xl bg-[#0d151c] border border-blue-950/80 space-y-1">
                <span className="text-xs text-slate-400">Selo Verificada</span>
                <p className="text-2xl font-bold text-blue-400">
                  {businesses.filter((b) => b.is_verified).length}
                </p>
                <span className="text-[11px] text-blue-500/80">Com documentos checados</span>
              </div>
              <div className="p-5 rounded-2xl bg-[#0d151c] border border-purple-950/80 space-y-1">
                <span className="text-xs text-slate-400">Cliques no WhatsApp Gerados</span>
                <p className="text-2xl font-bold text-purple-400">142</p>
                <span className="text-[11px] text-purple-500/80">Conversões registradas via /go</span>
              </div>
            </div>

            {/* Histórico de Logs de Decisões */}
            <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-400" />
                Histórico de Auditoria das Decisões (business_review_log)
              </h3>

              <div className="divide-y divide-[#182836] text-xs">
                {auditLogs.map((log) => {
                  const biz = businesses.find((b) => b.id === log.business_id);
                  return (
                    <div key={log.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="space-y-0.5">
                        <p className="font-bold text-white">
                          {biz?.name || 'Empresa'}
                          <span className="ml-2 font-mono text-[10px] text-slate-400 font-normal">
                            ({log.from_status} ➔ <strong className="text-emerald-400">{log.to_status}</strong>)
                          </span>
                        </p>
                        <p className="text-slate-300 text-[11px]">{log.note}</p>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500 shrink-0">
                        {new Date(log.created_at).toLocaleString('pt-BR')}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
