import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ type: string; id: string }> }
) {
  const { type, id } = await params;
  const userAgent = request.headers.get('user-agent') || '';
  const referer = request.headers.get('referer') || '';
  const clientIp =
    request.headers.get('cf-connecting-ip') ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-real-ip') ||
    '127.0.0.1';

  // Validação preliminar do tipo de contato (inclui 'job' da Sprint V3)
  if (!['whatsapp', 'phone', 'website', 'job'].includes(type)) {
    return new NextResponse('Tipo de contato ou redirecionamento inválido', { status: 400 });
  }

  // Encaminha requisição para o backend registrar a métrica no banco (contact_events)
  const backendBase = process.env.INTERNAL_API_URL || 'http://backend:8000/api/v1';
  try {
    const backendRes = await fetch(`${backendBase}/go/${type}/${id}`, {
      method: 'GET',
      headers: {
        'User-Agent': userAgent,
        'Referer': referer,
        'X-Forwarded-For': clientIp,
        'X-Real-IP': clientIp,
      },
      redirect: 'manual',
    });

    const location = backendRes.headers.get('location');
    if (location) {
      const res = NextResponse.redirect(location, { status: 307 });
      res.headers.set('Referrer-Policy', 'no-referrer');
      return res;
    }

    if (backendRes.status === 404) {
      return new NextResponse('Vaga ou empresa não encontrada ou não mais disponível.', { status: 404 });
    }
  } catch (err) {
    console.warn(`[GO_REDIRECT] Falha ao comunicar com backend para ID ${id}:`, err);
  }

  // Fallback para URL direta via rewrites
  const redirectUrl = `/api/v1/go/${type}/${id}`;
  return NextResponse.redirect(new URL(redirectUrl, request.url), { status: 307 });
}

