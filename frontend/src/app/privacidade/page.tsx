'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Shield, ArrowLeft, Lock, UserCheck, AlertTriangle, CheckCircle, Mail, Send } from 'lucide-react';
import { BrasilLogo } from '@/components/BrasilLogo';

export default function PrivacidadePage() {
  const [formType, setFormType] = useState('deletion');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [details, setDetails] = useState('');
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMsg(null);

    try {
      const res = await fetch('/api/v1/privacy/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_type: formType,
          email,
          phone: phone || null,
          details: details || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Não foi possível registrar a solicitação no momento.');
      }

      setStatusMsg({
        type: 'success',
        text: 'Sua solicitação de titular de dados foi protocolada com sucesso. Nossa equipe de privacidade (DPO) processará sua requisição no prazo legal de até 15 dias úteis.',
      });
      setEmail('');
      setPhone('');
      setDetails('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao enviar a solicitação. Tente novamente mais tarde.';
      setStatusMsg({
        type: 'error',
        text: msg,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-200">
      {/* Top Header */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 sticky top-0 z-40 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-slate-300 hover:text-amber-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Voltar ao Início</span>
          </Link>
          <div className="flex items-center gap-2">
            <BrasilLogo size={24} className="w-6 h-6 !rounded-md" />
            <span className="font-semibold text-white text-sm">Patriota Indica</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-[#0d151c] border border-[#182836] rounded-2xl p-6 sm:p-10 shadow-xl space-y-8">
          <div className="border-b border-[#182836] pb-6">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
              <Shield className="w-4 h-4" />
              <span>Conformidade com a Lei Geral de Proteção de Dados (Lei nº 13.709/2018)</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Política de Privacidade</h1>
            <p className="text-sm text-slate-400 mt-2">
              Última atualização: Outubro de 2026 • Versão 2.0 (Em conformidade com a LGPD e recomendações da ANPD)
            </p>
          </div>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Lock className="w-5 h-5 text-emerald-400" />
              1. Controlador de Dados e Encarregado (DPO)
            </h2>
            <p>
              O <strong>Patriota Indica</strong> atua como Controlador no tratamento dos dados pessoais coletados na plataforma. Para garantir total respeito à privacidade e cumprimento rigoroso da LGPD, disponibilizamos um canal direto e permanente com nosso Encarregado de Proteção de Dados (Data Protection Officer):
            </p>
            <div className="p-4 rounded-xl bg-[#121e29] border border-[#182836] flex items-center gap-4 text-xs">
              <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
                <Mail className="w-5 h-5" />
              </div>
              <div>
                <p className="font-semibold text-white">Encarregado pelo Tratamento de Dados Pessoais (DPO)</p>
                <p className="text-slate-400">Canal exclusivo de privacidade e direitos do titular:</p>
                <a href="mailto:dpo@patriotaindica.com.br" className="text-amber-400 hover:underline font-mono">
                  dpo@patriotaindica.com.br
                </a>
              </div>
            </div>
          </section>

          {/* CLÁUSULA DESTACADA: DADOS SENSÍVEIS E CARTA DE PRINCÍPIOS */}
          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <div className="p-5 rounded-2xl bg-gradient-to-br from-amber-950/40 to-slate-900 border-2 border-amber-500/60 shadow-lg space-y-3">
              <div className="flex items-center gap-2 text-amber-300 font-bold text-base">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                2. AVISO DESTACADO: Tratamento de Dados Pessoais Sensíveis (Art. 5º, II da LGPD)
              </div>
              <p className="text-xs text-amber-100/90 leading-relaxed">
                Ao cadastrar uma empresa ou atividade como Microempreendedor Individual (MEI), profissional autônomo ou pessoa física identificável, a declaração voluntária de adesão à <strong>Carta de Princípios da Liberdade</strong> (que contempla valores como defesa da família, ética ocidental, livre iniciativa e direito de propriedade) pode refletir convicções de natureza filosófica, moral ou política.
              </p>
              <div className="text-xs text-amber-200/90 space-y-1.5 border-t border-amber-800/40 pt-3">
                <p>
                  <strong>Base Legal e Consentimento Específico (Art. 11, I da LGPD):</strong> O tratamento desses dados ocorre estritamente mediante o seu consentimento específico, livre, informado e destacado, com a única e exclusiva finalidade de integrar a comunidade de estabelecimentos identificados com esses preceitos éticos e comerciais.
                </p>
                <p>
                  <strong>Direito de Revogação:</strong> Você possui o direito inalienável de revogar este consentimento a qualquer instante, o que resultará na imediata exclusão do vínculo e despublicação do perfil da plataforma, sem qualquer ônus.
                </p>
              </div>
            </div>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-emerald-400" />
              3. Dados Coletados e Finalidades
            </h2>
            <ul className="list-disc list-inside space-y-2 pl-2">
              <li>
                <strong>Dados Cadastrais da Empresa:</strong> Nome comercial, razão social, CNPJ (opcional), categoria/nicho de atuação, descrição de produtos/serviços, fotos/logotipo e redes sociais. Finalidade: exibição pública no diretório para busca e recomendação.
              </li>
              <li>
                <strong>Endereço e Geolocalização de MEIs:</strong> Reconhecendo que muitos MEIs e profissionais autônomos operam em residência particular, a plataforma adota o princípio da minimização da privacidade por padrão (<em>Privacy by Default</em>): somente o bairro e a cidade são exibidos publicamente, preservando o número do logradouro a menos que expressamente autorizado pelo titular.
              </li>
              <li>
                <strong>Canais de Contato:</strong> Telefone/WhatsApp e e-mail comercial. Finalidade: permitir que potenciais clientes entrem em contato direto com seu negócio.
              </li>
              <li>
                <strong>Dados de Acesso Técnico:</strong> Registros de conexão (endereço IP criptografado em hash e timestamp), estritamente para segurança contra fraudes e cumprimento do Marco Civil da Internet (Lei nº 12.965/2014, art. 15).
              </li>
            </ul>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white">4. Não Compartilhamento e Não Venda de Dados</h2>
            <p>
              O Patriota Indica <strong>não comercializa</strong> dados pessoais em nenhuma hipótese, nem compartilha cadastros com partidos políticos, comitês eleitorais ou terceiros para fins de marketing não relacionado. As informações comerciais publicadas no diretório são aquelas que o próprio anunciante optou por tornar públicas para fins de atração de clientes.
            </p>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white">5. Seus Direitos como Titular (Art. 18 da LGPD)</h2>
            <p>
              Em conformidade com o artigo 18 da LGPD, você pode a qualquer momento:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-[#121e29] border border-[#182836]">
                <strong className="text-white">Confirmação e Acesso:</strong> Confirmar a existência de tratamento e acessar seus dados cadastrados.
              </div>
              <div className="p-3 rounded-xl bg-[#121e29] border border-[#182836]">
                <strong className="text-white">Correção:</strong> Solicitar a correção imediata de dados incompletos, inexatos ou desatualizados.
              </div>
              <div className="p-3 rounded-xl bg-[#121e29] border border-[#182836]">
                <strong className="text-white">Anonimização ou Exclusão:</strong> Requerer a exclusão completa e definitiva de seu cadastro e histórico.
              </div>
              <div className="p-3 rounded-xl bg-[#121e29] border border-[#182836]">
                <strong className="text-white">Revogação do Consentimento:</strong> Revogar expressamente o consentimento da Carta de Princípios.
              </div>
            </div>
          </section>

          {/* FORMULÁRIO INTERATIVO DO TITULAR DE DADOS */}
          <section className="space-y-4 pt-4 border-t border-[#182836]">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Send className="w-5 h-5 text-amber-400" />
              Canal de Atendimento ao Titular de Dados
            </h2>
            <p className="text-xs text-slate-400">
              Utilize o formulário oficial abaixo para exercer seus direitos de privacidade perante o Encarregado (DPO). O protocolo será enviado ao nosso sistema com prazo de resposta de até 15 dias úteis.
            </p>

            <form onSubmit={handleSubmit} className="p-5 rounded-2xl bg-[#121e29] border border-[#182836] space-y-4 text-xs">
              {statusMsg && (
                <div
                  className={`p-3 rounded-xl border flex items-center gap-2 ${
                    statusMsg.type === 'success'
                      ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-200'
                      : 'bg-red-950/80 border-red-500/50 text-red-200'
                  }`}
                >
                  <CheckCircle className="w-4 h-4 shrink-0" />
                  <span>{statusMsg.text}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Tipo de Solicitação *</label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:outline-none focus:border-amber-400"
                  >
                    <option value="deletion">Exclusão Definitiva de Perfil e Dados Pessoais</option>
                    <option value="revocation">Revogação do Consentimento da Carta de Princípios</option>
                    <option value="export">Exportação / Cópia dos Meus Dados (Portabilidade)</option>
                    <option value="correction">Correção de Dados Cadastrais Incorretos</option>
                    <option value="information">Dúvidas sobre o Tratamento de Dados</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Seu E-mail Cadastrado *</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@suaempresa.com.br"
                    className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Telefone / WhatsApp (para confirmação de titularidade)</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="(19) 99999-9999"
                  className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Detalhes Adicionais (opcional)</label>
                <textarea
                  rows={3}
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  placeholder="Informe o nome da empresa ou detalhes para agilizar a localização do registro..."
                  className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:outline-none focus:border-amber-400 resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-[#070b0e] font-bold transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Protocolando...' : 'Protocolar Solicitação de Privacidade'}
              </button>
            </form>
          </section>

          <div className="pt-6 border-t border-[#182836] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
            <span>Encarregado pelo Tratamento de Dados Pessoais (DPO): dpo@patriotaindica.com.br</span>
            <Link href="/termos" className="text-amber-400 hover:underline">
              Ver Termos de Uso &rarr;
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
