export const CATEGORY_DEFAULT_BANNERS: Record<string, string> = {
  // 1. Serviços Residenciais & Reparos
  eletricista: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=800&q=80',
  'encanador-desentupidora': 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80',
  'ar-condicionado-climatizacao': 'https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=800&q=80',
  'pintor-reformas': 'https://images.unsplash.com/photo-1589939705384-5185137a7f0f?auto=format&fit=crop&w=800&q=80',
  chaveiro: 'https://images.unsplash.com/photo-1582139329536-e7284fece509?auto=format&fit=crop&w=800&q=80',
  marcenaria: 'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?auto=format&fit=crop&w=800&q=80',
  serralheria: 'https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?auto=format&fit=crop&w=800&q=80',
  vidracaria: 'https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80',
  'diarista-limpeza': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&q=80',
  dedetizadora: 'https://images.unsplash.com/photo-1628177142898-93e36e4e3a50?auto=format&fit=crop&w=800&q=80',
  jardinagem: 'https://images.unsplash.com/photo-1558904541-efa8c4a08931?auto=format&fit=crop&w=800&q=80',
  'fretes-mudancas': 'https://images.unsplash.com/photo-1600518464441-9154a4dea21b?auto=format&fit=crop&w=800&q=80',

  // 2. Automotivo
  'mecanica-autoeletrica': 'https://images.unsplash.com/photo-1486006920555-c77dce18193b?auto=format&fit=crop&w=800&q=80',
  'funilaria-pintura': 'https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=800&q=80',
  'borracharia-pneus': 'https://images.unsplash.com/photo-1578844251758-2f71da64c96f?auto=format&fit=crop&w=800&q=80',
  'lava-rapido': 'https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?auto=format&fit=crop&w=800&q=80',

  // 3. Tecnologia & Manutenção
  'celulares-tablets': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80',
  'informatica-redes': 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=800&q=80',
  'seguranca-eletronica': 'https://images.unsplash.com/photo-1557597774-9d273605dfa9?auto=format&fit=crop&w=800&q=80',

  // 4. Saúde & Beleza
  'barbearia-salao': 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=800&q=80',
  'estetica-beleza': 'https://images.unsplash.com/photo-1560750588-73207b1ef5b8?auto=format&fit=crop&w=800&q=80',
  'personal-fisioterapia': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=800&q=80',

  // 5. Pets
  'pet-shop-banho-tosa': 'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=800&q=80',
  veterinaria: 'https://images.unsplash.com/photo-1628009368231-7bb7cfcb0def?auto=format&fit=crop&w=800&q=80',

  // 6. Alimentação
  'marmitas-alimentacao': 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80',
  'padaria-confeitaria': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=800&q=80',
  'hortifruti-organicos': 'https://images.unsplash.com/photo-1610348725531-843dff563e2c?auto=format&fit=crop&w=800&q=80',
  'agua-gas': 'https://images.unsplash.com/photo-1548839140-29a749e1bc4e?auto=format&fit=crop&w=800&q=80',

  // 7. Comércio & Outros
  'materiais-construcao': 'https://images.unsplash.com/photo-1504307651554-66914ee56a38?auto=format&fit=crop&w=800&q=80',
  floricultura: 'https://images.unsplash.com/photo-1561181286-d3fee7d55364?auto=format&fit=crop&w=800&q=80',
  'costura-ajustes': 'https://images.unsplash.com/photo-1528458876861-544fd1761a91?auto=format&fit=crop&w=800&q=80',
  'papelaria-presentes': 'https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=800&q=80',

  default: 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=800&q=80',
};

export function getBusinessBannerUrl(business: {
  banner_url?: string | null;
  category_slug?: string | null;
}): string {
  if (business.banner_url && business.banner_url.trim()) {
    return business.banner_url.trim();
  }
  const slug = (business.category_slug || '').toLowerCase().trim();
  return CATEGORY_DEFAULT_BANNERS[slug] || CATEGORY_DEFAULT_BANNERS.default;
}
