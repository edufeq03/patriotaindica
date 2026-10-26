import { NextRequest, NextResponse } from 'next/server';
import { INITIAL_BUSINESSES } from '@/lib/mockData';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ type: string; id: string }> }
) {
  const { type, id } = await params;
  const userAgent = request.headers.get('user-agent') || '';
  const referer = request.headers.get('referer') || '';

  // Buscar empresa aprovada
  const business = INITIAL_BUSINESSES.find(b => b.id === id);

  if (!business) {
    return new NextResponse('Empresa não encontrada ou inativa', { status: 404 });
  }

  // Gravar métrica no console / telemetria
  console.log(`[CLICK_METRIC] Type: ${type} | Business: ${business.name} (${business.id}) | City: ${business.city}`);

  let destination = '';

  if (type === 'whatsapp') {
    const cleanNumber = business.whatsapp.replace(/\D/g, '');
    const fullNumber = cleanNumber.startsWith('55') ? cleanNumber : `55${cleanNumber}`;
    const defaultMsg = `Olá! Encontrei seu negócio no Guia Local e gostaria de informações/orçamento sobre ${business.name}.`;
    destination = `https://wa.me/${fullNumber}?text=${encodeURIComponent(defaultMsg)}`;
  } else if (type === 'phone') {
    const cleanPhone = (business.phone || business.whatsapp).replace(/\D/g, '');
    destination = `tel:${cleanPhone}`;
  } else if (type === 'website') {
    if (!business.website) {
      return new NextResponse('Site não cadastrado', { status: 400 });
    }
    destination = business.website.startsWith('http') ? business.website : `https://${business.website}`;
  } else {
    return new NextResponse('Tipo de contato inválido', { status: 400 });
  }

  return NextResponse.redirect(destination, { status: 307 });
}
