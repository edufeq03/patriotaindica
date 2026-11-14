import { NextRequest, NextResponse } from 'next/server';
import { getBackendUrl, setAuthCookies } from '@/lib/authServer';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const backendUrl = getBackendUrl();
    const clientIp =
      request.headers.get('cf-connecting-ip') ||
      request.headers.get('x-forwarded-for') ||
      '127.0.0.1';

    const res = await fetch(`${backendUrl}/businesses/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': clientIp,
      },
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => null);

    if (res.ok && data?.access_token) {
      const response = NextResponse.json({
        success: true,
        message: data.message,
        business_id: data.business_id,
        status: data.status,
        user: data.user,
      });

      // Emite cookies HttpOnly de sessão imediatos para o Dono
      setAuthCookies(response, data.access_token, data.refresh_token, data.user?.role || 'owner');
      return response;
    }

    return NextResponse.json(
      { detail: data?.detail || 'Erro ao realizar cadastro.' },
      { status: res.status || 400 }
    );
  } catch (err: unknown) {
    const errorMsg =
      err instanceof Error
        ? err.message
        : 'Não foi possível conectar ao servidor backend.';
    return NextResponse.json({ detail: errorMsg }, { status: 502 });
  }
}

