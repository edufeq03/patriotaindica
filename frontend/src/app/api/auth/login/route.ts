import { NextRequest, NextResponse } from 'next/server';
import {
  clearAuthCookies,
  getBackendUrl,
  setAuthCookies,
  createLocalSessionTokens,
  AuthUserPayload,
} from '@/lib/authServer';

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

    const cleanUsername = String(username).trim().toLowerCase();
    const cleanPassword = String(password).trim();

    // 1. Tenta autenticar contra o backend FastAPI
    let backendErrorDetail: string | null = null;
    try {
      const backendUrl = getBackendUrl();
      const formData = new URLSearchParams();
      formData.append('username', cleanUsername);
      formData.append('password', cleanPassword);

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

      if (res.ok) {
        const data = await res.json();
        const response = NextResponse.json({
          success: true,
          user: data.user,
        });
        setAuthCookies(response, data.access_token, data.refresh_token, data.user?.role);
        return response;
      }

      const errorData = await res.json().catch(() => null);
      backendErrorDetail = errorData?.detail || 'Credenciais inválidas.';
      return NextResponse.json(
        { detail: backendErrorDetail },
        { status: res.status }
      );
    } catch {
      return NextResponse.json(
        { detail: 'Servidor de autenticação indisponível. Tente novamente em instantes.' },
        { status: 503 }
      );
    }
  } catch (err: unknown) {
    const errorMessage =
      err instanceof Error
        ? err.message
        : 'Falha na comunicação com o servidor de autenticação.';
    return NextResponse.json({ detail: errorMessage }, { status: 500 });
  }
}

