'use client';

import React from 'react';
import { ShieldCheck, Scale, Award, HeartHandshake, CheckCircle2, X, ExternalLink } from 'lucide-react';

interface ManifestoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccept?: () => void;
  showAcceptButton?: boolean;
}

export const MANIFESTO_VERSION = 'v1.0-2026';

export default function ManifestoModal({
  isOpen,
  onClose,
  onAccept,
  showAcceptButton = false
}: ManifestoModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-2xl max-h-[90vh] flex flex-col rounded-2xl border border-amber-500/30 bg-[#070b0e] shadow-2xl shadow-amber-500/10 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Decorativo com Faixa Verde e Amarela Sutil */}
        <div className="h-1.5 w-full bg-gradient-to-r from-emerald-600 via-amber-500 to-blue-600" />

        <div className="p-6 border-b border-gray-800 flex items-start justify-between bg-gradient-to-b from-[#0d151c] to-[#070b0e]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                Estatuto da Rede de Afinidade
              </span>
              <h2 className="text-xl font-bold text-white mt-1">Carta de Princípios e Valores da Liberdade</h2>
              <p className="text-xs text-gray-400">Compromisso Ético e Moral dos Negócios Signatários • Versão {MANIFESTO_VERSION}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Conteúdo com Scroll */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm text-gray-300 leading-relaxed scrollbar-thin scrollbar-thumb-gray-800">
          {/* Apresentação */}
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/20 text-amber-200/90 text-xs sm:text-sm">
            <p className="font-medium">
              O <strong className="text-amber-400">Patriota Indica</strong> é um clube de negócios e rede de afinidade privada, 
              fundada na livre associação (Art. 5º, XVII da CF) e na autonomia da vontade (Art. 421 do Código Civil). 
              Reunimos empresas, profissionais e prestadores que voluntariamente compartilham e praticam os seguintes pilares inegociáveis:
            </p>
          </div>

          {/* Pilares */}
          <div className="space-y-4">
            {/* Pilar 1 */}
            <div className="p-4 rounded-xl bg-[#0b1219] border border-emerald-500/20 flex gap-4">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex-shrink-0 flex items-center justify-center text-emerald-400">
                <Scale className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-emerald-400 text-sm">1. Livre Iniciativa & Economia de Mercado</h3>
                <p className="text-xs text-gray-300 mt-1">
                  Crença absoluta no poder do empreendedorismo, da livre concorrência e do mérito individual como motores da prosperidade. 
                  Repúdio ao intervencionismo estatal asfixiante, à burocracia predatória e a privilégios corporativistas.
                </p>
              </div>
            </div>

            {/* Pilar 2 */}
            <div className="p-4 rounded-xl bg-[#0b1219] border border-blue-500/20 flex gap-4">
              <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/30 flex-shrink-0 flex items-center justify-center text-blue-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-blue-400 text-sm">2. Inviolabilidade da Propriedade Privada & Liberdades Fundamentais</h3>
                <p className="text-xs text-gray-300 mt-1">
                  Respeito sagrado ao fruto do trabalho honesto, à segurança jurídica, ao direito de propriedade e às liberdades civis 
                  básicas: liberdade de expressão, de culto, de locomoção e de autodeterminação econômica.
                </p>
              </div>
            </div>

            {/* Pilar 3 */}
            <div className="p-4 rounded-xl bg-[#0b1219] border border-amber-500/20 flex gap-4">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex-shrink-0 flex items-center justify-center text-amber-400">
                <Award className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-400 text-sm">3. Ética Cristã/Ocidental, Família & Retidão Comercial</h3>
                <p className="text-xs text-gray-300 mt-1">
                  Reconhecimento da família como núcleo basilar da sociedade civilizada. Compromisso com a palavra dada, pontualidade, 
                  honestidade inabalável nas relações de consumo, preços justos e respeito incondicional a clientes, fornecedores e colaboradores.
                </p>
              </div>
            </div>

            {/* Pilar 4 */}
            <div className="p-4 rounded-xl bg-[#0b1219] border border-gray-700/40 flex gap-4">
              <div className="w-9 h-9 rounded-lg bg-gray-800 border border-gray-700 flex-shrink-0 flex items-center justify-center text-amber-400">
                <HeartHandshake className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-sm">4. Prosperidade Comunitária & Cooperação Voluntária</h3>
                <p className="text-xs text-gray-300 mt-1">
                  Compromisso de priorizar negócios, contratações e parcerias com quem apoia esses mesmos valores, 
                  gerando um círculo virtuoso de riqueza local, geração de empregos e fortalecimento da nossa comunidade.
                </p>
              </div>
            </div>
          </div>

          {/* Enquadramento Legal e Garantias */}
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs text-gray-400 space-y-2">
            <div className="font-semibold text-gray-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Garantias Jurídicas e Relações de Consumo
            </div>
            <p>
              • <strong>Atendimento Universal ao Consumidor:</strong> Os signatários comprometem-se a atender a todos os cidadãos e clientes 
              com excelência e urbanidade, sem qualquer discriminação política, religiosa ou ideológica, em estrita observância ao Código de Defesa do Consumidor (CDC).
            </p>
            <p>
              • <strong>Curadoria Privada de Parceiros:</strong> A seleção para exibição no catálogo representa a manifestação legítima do direito 
              de associação e endosso privado, fundada na identidade de princípios éticos e não em filiação ou partidária compulsória.
            </p>
            <p>
              • <strong>Proteção de Dados (LGPD):</strong> Não coletamos nem exigimos dados partidários sensíveis. O único critério é a manifestação 
              livre e voluntária de subscrição a esta Carta de Princípios.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-gray-800 bg-[#0d151c] flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-xs text-gray-400 text-center sm:text-left">
            Ao subscrever, sua empresa recebe o selo oficial de Signatária Patriota Indica.
          </span>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl border border-gray-700 text-xs font-semibold text-gray-300 hover:bg-gray-800 transition-colors"
            >
              Fechar
            </button>
            {showAcceptButton && onAccept && (
              <button
                onClick={() => {
                  onAccept();
                  onClose();
                }}
                className="flex-1 sm:flex-initial px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-600 to-amber-500 hover:from-amber-400 hover:to-amber-500 text-black font-bold text-xs shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4 text-black" />
                Subscrever Voluntariamente
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
