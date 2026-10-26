import Link from 'next/link';
import { Shield, ArrowLeft, CheckCircle, Scale, FileText } from 'lucide-react';

export const metadata = {
  title: 'Termos de Uso | Patriota Indica',
  description: 'Termos e Condições de Uso da plataforma Patriota Indica.',
};

export default function TermosPage() {
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
            <span className="w-6 h-6 rounded bg-emerald-950 border border-amber-500/50 text-amber-300 flex items-center justify-center font-bold text-xs">
              PI
            </span>
            <span className="font-semibold text-white text-sm">Patriota Indica</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-[#0d151c] border border-[#182836] rounded-2xl p-6 sm:p-10 shadow-xl space-y-8">
          <div className="border-b border-[#182836] pb-6">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-2">
              <FileText className="w-4 h-4" />
              <span>Documento Oficial de Uso da Plataforma</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Termos de Uso</h1>
            <p className="text-sm text-slate-400 mt-2">
              Última atualização: Outubro de 2026 • Versão 1.2
            </p>
          </div>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Scale className="w-5 h-5 text-emerald-400" />
              1. Objeto e Natureza da Plataforma
            </h2>
            <p>
              O <strong>Patriota Indica</strong> é um catálogo colaborativo e diretório nacional de descoberta de empresas, produtos e prestadores de serviços que compartilham dos valores da livre iniciativa, ética ocidental, integridade moral, direito de propriedade e preservação da família.
            </p>
            <p>
              A plataforma atua como ponte de visibilidade comercial entre consumidores e empreendedores. O Patriota Indica <strong>não</strong> é fornecedor dos produtos ou serviços anunciados, não intermedeia pagamentos e não se responsabiliza pelas transações comerciais, orçamentos, contratos ou obrigações civis celebradas entre clientes e estabelecimentos listados.
            </p>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              2. Cadastro e Critérios da Carta de Princípios
            </h2>
            <p>
              O cadastramento de empresas, profissionais autônomos e Microempreendedores Individuais (MEI) é voluntário e gratuito em sua modalidade básica.
            </p>
            <p>
              Para submeter uma empresa, o responsável declara, sob as penas da lei, a veracidade dos dados cadastrais e a subscrição livre e espontânea à <strong>Carta de Princípios da Liberdade</strong>. Toda candidatura é submetida a um processo de curadoria prévia e verificação comunitária antes da publicação definitiva.
            </p>
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 text-xs text-amber-200 space-y-2">
              <p className="font-semibold text-amber-300">Conduta e Diretrizes Editoriais:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>É estritamente vedada a publicação de conteúdos ilícitos, difamatórios, discriminatórios ou fraudulentos;</li>
                <li>Não é admitido o uso da plataforma para incitação à violência, condutas anticoncorrenciais ou apologia a crimes;</li>
                <li>Qualquer divergência insanável com a Carta de Princípios ou denúncia de fraude comprovada ensejará a despublicação imediata do cadastro.</li>
              </ul>
            </div>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              3. Responsabilidades do Titular do Estabelecimento
            </h2>
            <p>
              O titular ou administrador do perfil compromete-se a:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-300">
              <li>Manter canais de atendimento e contatos (WhatsApp, telefone, e-mail) atualizados e verídicos;</li>
              <li>Cumprir a legislação consumerista brasileira (Código de Defesa do Consumidor - Lei nº 8.078/1990);</li>
              <li>Honrar orçamentos, prazos e políticas de garantia divulgadas ao público;</li>
              <li>Informar prontamente qualquer alteração estrutural ou encerramento das atividades empresariais.</li>
            </ul>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white">4. Propriedade Intelectual e Uso de Marcas</h2>
            <p>
              As marcas, logotipos, slogans e imagens enviadas pelos estabelecimentos permanecem sob titularidade exclusiva de seus respectivos donos, que concedem ao Patriota Indica licença não exclusiva, gratuita e de âmbito nacional para exibição na plataforma.
            </p>
            <p>
              A marca, layout, arquitetura de software e banco de dados do Patriota Indica são protegidos pela legislação de propriedade intelectual e direitos autorais.
            </p>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white">5. Denúncias e Desativação de Perfil</h2>
            <p>
              A plataforma disponibiliza canal aberto para denúncias de inconsistências cadastrais, atendimento inidôneo ou descumprimento dos preceitos comunitários. O titular poderá, a qualquer tempo, solicitar o desligamento ou exclusão permanente do seu perfil através do e-mail <strong>contato@patriotaindica.com.br</strong> ou pelo formulário de privacidade.
            </p>
          </section>

          <section className="space-y-4 text-sm leading-relaxed text-slate-300">
            <h2 className="text-lg font-bold text-white">6. Foro e Disposições Gerais</h2>
            <p>
              Estes Termos de Uso são regidos pelas leis da República Federativa do Brasil. Para a resolução de eventuais litígios que não possam ser dirimidos amigavelmente, fica eleito o Foro da Comarca de Campinas/SP, com expressa renúncia a qualquer outro, por mais privilegiado que seja.
            </p>
          </section>

          <div className="pt-6 border-t border-[#182836] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
            <span>Dúvidas jurídicas ou contratuais? Fale com nossa equipe: contato@patriotaindica.com.br</span>
            <Link href="/privacidade" className="text-amber-400 hover:underline">
              Ver Política de Privacidade (LGPD) &rarr;
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
