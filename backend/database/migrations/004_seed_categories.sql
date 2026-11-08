-- ==============================================================================
-- Migration 004 / Seed: Initial Curated Categories
-- Description: Core taxonomy of local services, products, and hybrid businesses
--              tailored for Brazilian municipal launch (MVP).
-- ==============================================================================

INSERT INTO categories (name, slug, kind, icon_name, display_order)
VALUES
  -- 1. SERVIÇOS RESIDENCIAIS E REPAROS
  ('Eletricista', 'eletricista', 'service', 'zap', 1),
  ('Encanador e Desentupidora', 'encanador-desentupidora', 'service', 'droplets', 2),
  ('Ar-condicionado e Climatização', 'ar-condicionado-climatizacao', 'service', 'wind', 3),
  ('Pintor e Reformas', 'pintor-reformas', 'service', 'paint-brush', 4),
  ('Chaveiro 24h', 'chaveiro', 'service', 'key', 5),
  ('Marcenaria e Móveis Planejados', 'marcenaria', 'service', 'hammer', 6),
  ('Serralheria e Esquadrias', 'serralheria', 'service', 'shield', 7),
  ('Vidraçaria', 'vidracaria', 'service', 'square', 8),
  ('Diarista e Limpeza Profissional', 'diarista-limpeza', 'service', 'sparkles', 9),
  ('Dedetizadora e Controle de Pragas', 'dedetizadora', 'service', 'shield-alert', 10),
  ('Jardinagem e Paisagismo', 'jardinagem', 'service', 'flower-2', 11),
  ('Fretes e Mudanças', 'fretes-mudancas', 'service', 'truck', 12),

  -- 2. AUTOMOTIVO
  ('Mecânica e Autoelétrica', 'mecanica-autoeletrica', 'service', 'car', 13),
  ('Funilaria e Pintura Automotiva', 'funilaria-pintura', 'service', 'gauge', 14),
  ('Borracharia e Pneus', 'borracharia-pneus', 'service', 'disc', 15),
  ('Lava-Rápido e Estética Automotiva', 'lava-rapido', 'service', 'waves', 16),

  -- 3. TECNOLOGIA E MANUTENÇÃO
  ('Assistência de Celulares e Tablets', 'celulares-tablets', 'service', 'smartphone', 17),
  ('Manutenção de Computadores e Redes', 'informatica-redes', 'service', 'laptop', 18),
  ('Instalação de Câmeras e Segurança', 'seguranca-eletronica', 'service', 'cctv', 19),

  -- 4. SAÚDE, BELEZA E BEM-ESTAR
  ('Barbearia e Salão de Beleza', 'barbearia-salao', 'both', 'scissors', 20),
  ('Estética e Cuidados Pessoais', 'estetica-beleza', 'both', 'sparkle', 21),
  ('Personal Trainer e Fisioterapia', 'personal-fisioterapia', 'service', 'activity', 22),

  -- 5. PETS
  ('Pet Shop e Banho & Tosa', 'pet-shop-banho-tosa', 'both', 'paw-print', 23),
  ('Clínica Veterinária', 'veterinaria', 'service', 'stethoscope', 24),

  -- 6. ALIMENTAÇÃO E PRODUTOS LOCAIS
  ('Marmitas e Comida Caseira', 'marmitas-alimentacao', 'product', 'utensils', 25),
  ('Padaria e Confeitaria Artesanal', 'padaria-confeitaria', 'product', 'cake', 26),
  ('Hortifruti e Orgânicos', 'hortifruti-organicos', 'product', 'apple', 27),
  ('Água Mineral e Gás', 'agua-gas', 'product', 'flame', 28),

  -- 7. COMÉRCIO E MATERIAIS
  ('Materiais de Construção', 'materiais-construcao', 'both', 'hard-hat', 29),
  ('Flores e Plantas Ornamentais', 'floricultura', 'product', 'leaf', 30),
  ('Costura e Ajustes', 'costura-ajustes', 'service', 'needle', 31),
  ('Papelaria e Presentes', 'papelaria-presentes', 'product', 'book-open', 32),

  -- 8. SERVIÇOS PROFISSIONAIS E ESPECIALIZADOS
  ('Advocacia e Assessoria Jurídica', 'advocacia-juridico', 'service', 'scale', 33),
  ('Contabilidade e Finanças', 'contabilidade-fiscal', 'service', 'calculator', 34),
  ('Despachante Documentalista', 'despachante', 'service', 'file-text', 35),
  ('Psicologia e Saúde Mental', 'psicologia-saude-mental', 'service', 'brain', 36),
  ('Fisioterapia e Reabilitação', 'fisioterapia-reabilitacao', 'service', 'activity', 37),
  ('Odontologia e Dentista', 'odontologia-dentista', 'service', 'smile', 38),
  ('Nutrição e Dietética', 'nutricao-bem-estar', 'service', 'apple', 39),
  ('Manicure, Pedicure e Nail Art', 'manicure-pedicure', 'service', 'sparkles', 40),
  ('Sobrancelhas e Cílios', 'sobrancelhas-cilios', 'service', 'eye', 41),
  ('Tatuagem e Piercing', 'tatuagem-piercing', 'service', 'feather', 42),
  ('Fotografia e Filmagem', 'fotografia-filmagem', 'service', 'camera', 43),
  ('Festas, Decoração e Eventos', 'festas-eventos', 'service', 'gift', 44),
  ('DJ, Som e Iluminação', 'dj-som-iluminacao', 'service', 'music', 45),
  ('Aulas Particulares e Educação', 'aulas-particulares', 'service', 'graduation-cap', 46),
  ('Conserto de Eletrodomésticos', 'conserto-eletrodomesticos', 'service', 'wrench', 47),
  ('Tapeçaria e Reforma de Estofados', 'tapecaria-estofados', 'service', 'armchair', 48),
  ('Guincho e Reboque 24h', 'guincho-reboque-24h', 'service', 'truck', 49),
  ('Adestramento e Passeador Pet', 'adestramento-passeador-pet', 'service', 'paw-print', 50),
  ('Gesso, Drywall e Iluminação', 'gesso-drywall', 'service', 'layout', 51),
  ('Energia Solar e Fotovoltaica', 'energia-solar', 'service', 'sun', 52),
  ('Pizzaria e Hamburgueria', 'pizzaria-hamburgueria', 'both', 'pizza', 53),
  ('Gráfica Rápida e Comunicação Visual', 'grafica-comunicacao-visual', 'service', 'printer', 54)
ON CONFLICT (slug) DO UPDATE
SET
  name = EXCLUDED.name,
  kind = EXCLUDED.kind,
  icon_name = EXCLUDED.icon_name,
  display_order = EXCLUDED.display_order;

