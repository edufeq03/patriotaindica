import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ type: string; id: string }> }
) {
  const { type, id } = await params;
  const userAgent = request.headers.get('user-agent') || '';
  const referer = request.headers.get('referer') || '';

  // Validação preliminar do tipo de contato
  if (!['whatsapp', 'phone', 'website'].includes(type)) {
    return new NextResponse('Tipo de contato inválido', { status: 400 });
  }

  // Encaminha requisição para o backend registrar a métrica no banco (contact_events)
  const backendBase = process.env.INTERNAL_API_URL || 'http://backend:8000/api/v1';
  try {
    const backendRes = await fetch(`${backendBase}/go/${type}/${id}`, {
      method: 'GET',
      headers: {
        'User-Agent': userAgent,
        'Referer': referer,
      },
      redirect: 'manual',
    });

    const location = backendRes.headers.get('location');
    if (location) {
      return NextResponse.redirect(location, { status: 307 });
    }
  } catch (err) {
    console.warn(`[GO_REDIRECT] Falha ao comunicar com backend para ID ${id}:`, err);
  }

  // Fallback para URL direta via rewrites
  const redirectUrl = `/api/v1/go/${type}/${id}`;
  return NextResponse.redirect(new URL(redirectUrl, request.url), { status: 307 });
}

