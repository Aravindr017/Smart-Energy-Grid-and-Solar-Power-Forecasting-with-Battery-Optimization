import React from 'react';
import SectionHeader from './SectionHeader';

export default function ChartCard({ title, description, legend, children, className = '' }) {
  return (
    <section className={`surface-card p-5 ${className}`}>
      <SectionHeader title={title} description={description} actions={legend} />
      {children}
    </section>
  );
}
