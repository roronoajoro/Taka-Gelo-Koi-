/**
 * GoogleAuth.jsx
 * Google OAuth Login Component for React
 * 
 * Features:
 * - One-click Google login
 * - Automatic user creation/update
 * - Profile picture display
 * - Secure token handling
 */

import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { useState } from 'react';

// ============ CONFIGURATION ============
const GOOGLE_CLIENT_ID = "114576452021-8e52ima3s04sk72it2emvdic9a7d3006.apps.googleusercontent.com"; // Replace with your actual Client ID
const API_URL = "http://localhost:8000";


function GoogleAuth({ onLoginSuccess }) {
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Handle successful Google login
   * @param {Object} credentialResponse - Response from Google containing the ID token
   */
  const handleGoogleSuccess = async (credentialResponse) => {
    setIsLoading(true);
    setError(null);

    try {
      // Send Google's ID token to our backend for verification
      const response = await fetch(`${API_URL}/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: credentialResponse.credential  // Google's ID token (JWT)
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Authentication failed');
      }

      const data = await response.json();

      // Store user data in localStorage for session management
      localStorage.setItem('user', JSON.stringify({
        id: data.user_id,
        name: data.name,
        email: data.email,
        picture: data.picture,
      }));

      // Call parent component's success handler
      onLoginSuccess({
        id: data.user_id,
        name: data.name,
        email: data.email,
        picture: data.picture,
        isNewUser: data.is_new_user,
      });

      // Show welcome message for new users
      if (data.is_new_user) {
        console.log('Welcome! Your account has been created.');
      } else {
        console.log('Welcome back!');
      }

    } catch (err) {
      console.error('Google login error:', err);
      setError(err.message || 'Failed to login with Google');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle Google login failure
   */
  const handleGoogleError = () => {
    setError('Google login failed. Please try again.');
    console.error('Google login failed');
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="google-auth-container">
        <GoogleLogin
          onSuccess={handleGoogleSuccess}
          onError={handleGoogleError}
          useOneTap={true}  // Enable One-Tap login
          auto_select={false}  // Don't auto-select account
          theme="filled_blue"  // Button theme: 'outline' or 'filled_blue' or 'filled_black'
          size="large"  // Button size: 'large' or 'medium' or 'small'
          text="signin_with"  // Button text: 'signin_with', 'signup_with', or 'continue_with'
          shape="rectangular"  // Button shape: 'rectangular' or 'pill' or 'circle' or 'square'
          logo_alignment="left"  // Logo alignment: 'left' or 'center'
        />

        {/* Loading indicator */}
        {isLoading && (
          <div className="loading-message">
            <p>Logging in...</p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}
      </div>
    </GoogleOAuthProvider>
  );
}

export default GoogleAuth;


// ============ CSS STYLES ============
// Add this to your App.css:

/*
.google-auth-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin: 2rem 0;
}

.loading-message {
  color: #4285f4;
  font-size: 0.9rem;
}

.error-message {
  color: #ea4335;
  background-color: #fce8e6;
  border: 1px solid #ea4335;
  border-radius: 4px;
  padding: 0.75rem;
  margin-top: 1rem;
  font-size: 0.9rem;
}
*/
