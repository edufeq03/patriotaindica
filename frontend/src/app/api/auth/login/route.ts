import { NextRequest, NextResponse } from 'next/server';
import { clearAuthCookies, getBackendUrl, setAuthCookies } from '@/lib/authServer';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return NextResponse.json(
        { detail: 'Usuário e senha são obrigatórios.' },
        { status: 400 }
      );
    }

    const backendUrl = getBackendUrl();
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const clientIp =
      request.headers.get('cf-connecting-ip') ||
      request.headers.get('x-forwarded-for') ||
      '127.0.0.1';

    const res = await fetch(`${backendUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Forwarded-For': clientIp,
      },
      body: formData.toString(),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Credenciais inválidas.' },
        { status: res.status }
      );
    }

    const response = NextResponse.json({
      success: true,
      user: data.user,
    });

    setAuthCookies(response, data.access_token, data.refresh_token);
    return response;
  } catch (err: unknown) {
    const errorMessage = err instanceof Error ? err.message : 'Falha na comunicação com o servidor de autenticação.';
    return NextResponse.json(
      { detail: errorMessage },
      { status: 500 }
    );
  }
}
