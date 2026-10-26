import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { INITIAL_BUSINESSES } from '@/lib/mockData';
import BusinessProfileView from '@/components/BusinessProfileView';

interface Props {
  params: Promise<{
    city: string;
    category: string;
    slug: string;
  }>;
}

export async function generateStaticParams() {
  return INITIAL_BUSINESSES.filter((b) => b.status === 'approved').map((b) => ({
    city: `${b.city.toLowerCase()}-${b.state.toLowerCase()}`,
    category: b.category_slug,
    slug: b.slug,
  }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const business = INITIAL_BUSINESSES.find((b) => b.slug === slug && b.status === 'approved');

  if (!business) {
    return {
      title: 'Empresa Não Encontrada | Guia Local Curado',
      description: 'O perfil solicitado não está disponível ou ainda está em análise de curadoria.',
    };
  }

  return {
    title: `${business.name} | ${business.category_name} em ${business.city} - ${business.state}`,
    description: `${business.description.slice(0, 155)}... Contato direto no WhatsApp, atendimento verificado e curado.`,
    openGraph: {
      title: `${business.name} | ${business.category_name} em ${business.city}`,
      description: business.description,
      type: 'article',
      images: business.banner_url ? [business.banner_url] : [],
    },
  };
}

export default async function BusinessProfilePage({ params }: Props) {
  const { city, category, slug } = await params;
  const business = INITIAL_BUSINESSES.find((b) => b.slug === slug && b.status === 'approved');

  if (!business) {
    notFound();
  }

  return (
    <BusinessProfileView
      business={business}
      city={city}
      category={category}
      slug={slug}
    />
  );
}
