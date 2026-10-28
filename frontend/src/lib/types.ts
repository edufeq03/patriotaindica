export type ListingType = 'service' | 'product' | 'both';
export type ServiceMode = 'at_location' | 'at_customer' | 'both' | 'online';
export type BusinessStatus = 'draft' | 'pending_review' | 'needs_info' | 'approved' | 'rejected' | 'suspended';

export interface Category {
  id: string;
  name: string;
  slug: string;
  kind: ListingType;
  icon_name: string;
  display_order: number;
}

export interface Business {
  id: string;
  name: string;
  slug: string;
  description: string;
  listing_type: ListingType;
  service_mode: ServiceMode;
  service_radius_km?: number;
  serves_at_location?: boolean;
  serves_at_customer?: boolean;
  serves_online?: boolean;
  category_name: string;
  category_slug: string;
  whatsapp: string;
  phone?: string;
  website?: string;
  instagram?: string;
  street?: string;
  number?: string;
  neighborhood: string;
  city: string;
  state: string;
  postal_code?: string;
  show_full_address: boolean;
  latitude: number;
  longitude: number;
  logo_url?: string;
  banner_url?: string;
  status: BusinessStatus;
  is_verified: boolean;
  distance_km?: number;
  document_type?: 'CNPJ' | 'CPF';
  document_number?: string;
  cnpj_situation?: string;
  created_at: string;

  // Blindagem Jurídica: Adesão Voluntária à Carta de Princípios (Estatuto da Rede de Afinidade)
  accepted_manifesto?: boolean;
  accepted_manifesto_at?: string;
  manifesto_version?: string;
}

export interface ReviewLog {
  id: string;
  business_id: string;
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}
