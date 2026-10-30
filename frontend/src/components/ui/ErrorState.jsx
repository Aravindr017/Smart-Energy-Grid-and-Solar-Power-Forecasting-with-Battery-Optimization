import React from 'react';
import { AlertTriangle } from 'lucide-react';
import PrimaryButton from './PrimaryButton';

export default function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-900">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <h3 className="font-semibold">{title}</h3>
          {message && <p className="mt-1 text-sm text-red-800">{message}</p>}
          {onRetry && (
            <PrimaryButton className="mt-4 bg-red-700 hover:bg-red-800" onClick={onRetry}>
              Try again
            </PrimaryButton>
          )}
        </div>
      </div>
    </div>
  );
}
