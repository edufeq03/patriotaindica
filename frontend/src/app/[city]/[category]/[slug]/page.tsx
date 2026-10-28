import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { INITIAL_BUSINESSES } from '@/lib/mockData';
import { Business } from '@/lib/types';
import BusinessProfileView from '@/components/BusinessProfileView';
export const instant = false;

interface Props {
  params: Promise<{
    city: string;
    category: string;
    slug: string;
  }>;
}

export async function generateStaticParams() {
  const params = INITIAL_BUSINESSES.filter((b) => b.status === 'approved').map((b) => ({
    city: `${b.city.toLowerCase()}-${b.state.toLowerCase()}`,
    category: b.category_slug,
    slug: b.slug,
  }));

  // Requisito do Next.js 16 (Cache Components): generateStaticParams deve conter pelo menos 1 rota para validação de build
  if (params.length === 0) {
    return [{ city: 'sp-campinas', category: 'servicos', slug: 'exemplo' }];
  }
  return params;
}

/**
 * Busca dados da empresa pelo slug com tolerância a falhas:
 * 1. Tenta conexões de backend internas (Docker/Compose/Easypanel) e pública
 * 2. Faz fallback transparente para dados de semente (INITIAL_BUSINESSES) se offline ou semente
 */
async function fetchBusinessBySlug(slug: string): Promise<Business | null> {
  const candidateUrls = [
    process.env.INTERNAL_API_URL,
    'http://backend:8000/api/v1',
    'http://patriotaindica-backend:8000/api/v1',
    'http://127.0.0.1:8000/api/v1',
    'https://patriotaindica.com/api/v1',
  ].filter(Boolean) as string[];

  const uniqueUrls = Array.from(new Set(candidateUrls));

  for (const base of uniqueUrls) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(`${base}/businesses/by-slug/${encodeURIComponent(slug)}`, {
        signal: controller.signal,
        next: { revalidate: 60 },
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (data && data.id) {
          const primaryCat = data.categories?.find((c: any) => c.is_primary) || data.categories?.[0];
          const category_name = primaryCat?.name || 'Geral';
          const category_slug = primaryCat?.slug || 'geral';

          return {
            id: String(data.id),
            name: data.name || '',
            slug: data.slug || slug,
            description: data.description || '',
            listing_type: data.listing_type || 'service',
            service_mode: data.service_mode || 'at_location',
            service_radius_km: data.service_radius_km,
            category_name,
            category_slug,
            whatsapp: data.whatsapp || '',
            phone: data.phone || undefined,
            website: data.website || undefined,
            instagram: data.instagram || undefined,
            street: data.street || undefined,
            number: data.number || undefined,
            neighborhood: data.neighborhood || '',
            city: data.city || '',
            state: data.state || '',
            postal_code: data.postal_code || undefined,
            show_full_address: !!data.show_full_address,
            latitude: Number(data.latitude) || 0,
            longitude: Number(data.longitude) || 0,
            logo_url: data.logo_url || undefined,
            banner_url: data.banner_url || undefined,
            status: 'approved',
            is_verified: !!data.is_verified,
            created_at: data.created_at || new Date().toISOString(),
            accepted_manifesto: true,
            manifesto_version: 'v1.0-2026',
          };
        }
      }
    } catch {
      // Tenta próximo endpoint candidato
    }
  }

  // Fallback para sementes locais caso ainda não esteja no banco
  const mock = INITIAL_BUSINESSES.find(
    (b) => b.slug.toLowerCase() === slug.toLowerCase() && b.status === 'approved'
  );
  return mock || null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const cleanSlug = decodeURIComponent(slug).trim().toLowerCase();
  const business = await fetchBusinessBySlug(cleanSlug);

  if (!business) {
    return {
      title: 'Empresa Não Encontrada | Patriota Indica',
      description: 'O perfil solicitado não está disponível ou ainda está em análise de curadoria.',
    };
  }

  return {
    title: `${business.name} | ${business.category_name} em ${business.city} - ${business.state}`,
    description: `${(business.description || '').slice(0, 155)}... Contato direto no WhatsApp, atendimento verificado e curado.`,
    openGraph: {
      title: `${business.name} | ${business.category_name} em ${business.city}`,
      description: business.description || '',
      type: 'article',
      images: business.banner_url ? [business.banner_url] : [],
    },
  };
}

export default async function BusinessProfilePage({ params }: Props) {
  const { city, category, slug } = await params;
  const cleanSlug = decodeURIComponent(slug).trim().toLowerCase();
  const business = await fetchBusinessBySlug(cleanSlug);

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

