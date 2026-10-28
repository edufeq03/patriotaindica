import { NextRequest, NextResponse } from 'next/server';
import { clearAuthCookies, getBackendUrl, setAuthCookies } from '@/lib/authServer';

export async function POST(request: NextRequest) {
  try {
    const refreshToken = request.cookies.get('refresh_token')?.value;

    if (!refreshToken) {
      const response = NextResponse.json(
        { detail: 'Nenhuma sessão ativa encontrada.' },
        { status: 401 }
      );
      clearAuthCookies(response);
      return response;
    }

    const backendUrl = getBackendUrl();
    const clientIp =
      request.headers.get('cf-connecting-ip') ||
      request.headers.get('x-forwarded-for') ||
      '127.0.0.1';

    const res = await fetch(`${backendUrl}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': clientIp,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await res.json();

    if (!res.ok) {
      const response = NextResponse.json(
        { detail: data.detail || 'Sessão expirada. Faça login novamente.' },
        { status: 401 }
      );
      clearAuthCookies(response);
      return response;
    }

    const response = NextResponse.json({
      success: true,
      user: data.user,
    });

    setAuthCookies(response, data.access_token, data.refresh_token);
    return response;
  } catch {
    const response = NextResponse.json(
      { detail: 'Erro ao renovar sessão.' },
      { status: 500 }
    );
    return response;
  }
}
