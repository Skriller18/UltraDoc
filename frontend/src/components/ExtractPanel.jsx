import React, { useState } from 'react';

const FIELD_LABELS = {
  shipment_id: 'Shipment ID',
  shipper: 'Shipper',
  consignee: 'Consignee',
  pickup_datetime: 'Pickup Date/Time',
  delivery_datetime: 'Delivery Date/Time',
  equipment_type: 'Equipment Type',
  mode: 'Mode',
  rate: 'Rate',
  currency: 'Currency',
  weight: 'Weight',
  carrier_name: 'Carrier Name',
  reference_id: 'Reference ID',
  load_id: 'Load ID',
  po_number: 'PO Number',
  container_id: 'Container ID',
  booking_date: 'Booking Date',
  agreed_amount: 'Agreed Amount',
  dispatcher_name: 'Dispatcher Name',
  dispatcher_phone: 'Dispatcher Phone',
  dispatcher_email: 'Dispatcher Email',

  invoice_number: 'Invoice Number',
  invoice_date: 'Invoice Date',
  bill_to: 'Bill To',
  remit_to: 'Remit To',
  subtotal: 'Subtotal',
  tax: 'Tax',
  total: 'Total',
  due_date: 'Due Date',

  packing_list_number: 'Packing List Number',
  total_packages: 'Total Packages',
  total_weight: 'Total Weight',
  weight_unit: 'Weight Unit',
};

export function ExtractPanel({ data, onClose, isLoading }) {
  const [copied, setCopied] = useState(false);

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="extract-panel">
      <div className="extract-header">
        <h2 className="extract-title">Structured Extraction</h2>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>
      
      <div className="extract-content">
        {isLoading ? (
          <div className="empty-state">
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p style={{ marginTop: '16px' }}>Extracting shipment data...</p>
          </div>
        ) : data ? (
          Object.entries(data).map(([key, value]) => {
            // Skip internal keys
            if (key.startsWith('_')) return null;
            
            return (
              <div key={key} className="extract-field">
                <div className="field-label">{FIELD_LABELS[key] || key}</div>
                <div className={`field-value ${value === null ? 'null' : ''}`}>
                  {value !== null ? String(value) : 'Not found'}
                </div>
              </div>
            );
          })
        ) : (
          <div className="empty-state">
            <p className="empty-state-text">No data extracted yet</p>
          </div>
        )}
      </div>
      
      {data && !isLoading && (
        <div className="extract-actions">
          <button className="copy-json-btn" onClick={handleCopyJson}>
            {copied ? '✓ Copied!' : 'Copy as JSON'}
          </button>
        </div>
      )}
    </div>
  );
}
