import { NextRequest, NextResponse } from 'next/server';
import {
  clearAuthCookies,
  getBackendUrl,
  setAuthCookies,
  verifyTokenLocally,
} from '@/lib/authServer';

export async function GET(request: NextRequest) {
  try {
    let accessToken = request.cookies.get('access_token')?.value;
    const refreshToken = request.cookies.get('refresh_token')?.value;

    const backendUrl = getBackendUrl();

    // 1. Tenta buscar perfil com o access_token atual no backend
    if (accessToken) {
      try {
        const res = await fetch(`${backendUrl}/auth/me`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        if (res.ok) {
          const user = await res.json();
          return NextResponse.json({ authenticated: true, user });
        }
      } catch {
        // Backend indisponível ou em modo desconectado: tenta validação local
      }

      // Validação local do JWT com o segredo criptográfico da aplicação
      const localUser = await verifyTokenLocally(accessToken);
      if (localUser) {
        return NextResponse.json({ authenticated: true, user: localUser });
      }
    }

    // 2. Se houver refresh_token, tenta rotação transparente
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${backendUrl}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          accessToken = refreshData.access_token;

          const response = NextResponse.json({
            authenticated: true,
            user: refreshData.user,
          });

          setAuthCookies(
            response,
            refreshData.access_token,
            refreshData.refresh_token,
            refreshData.user?.role
          );
          return response;
        }
      } catch {
        // Backend indisponível
      }

      const localRefreshUser = await verifyTokenLocally(refreshToken);
      if (localRefreshUser) {
        return NextResponse.json({ authenticated: true, user: localRefreshUser });
      }
    }

    // 3. Sem tokens válidos
    const response = NextResponse.json(
      { authenticated: false, user: null },
      { status: 401 }
    );
    clearAuthCookies(response);
    return response;
  } catch {
    return NextResponse.json(
      { authenticated: false, user: null },
      { status: 500 }
    );
  }
}

