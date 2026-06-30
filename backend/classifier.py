import re


class AthenaClassifier:

    def clean_text(self, text):
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        return text


    def classify(self, text):

        text = self.clean_text(text)

        quotation_words = [
            "quotation",
            "quote",
            "عرض سعر",
            "عرض مالي",
            "السعر",
            "الاسعار",
            "price offer"
        ]

        tender_words = [
            "tender",
            "مناقصة",
            "عطاء",
            "bid",
            "closing date",
            "تاريخ الإغلاق"
        ]

        invoice_words = [
            "invoice",
            "tax invoice",
            "فاتورة",
            "vat",
            "trn"
        ]

        purchase_order_words = [
            "purchase order",
            "po number",
            "أمر شراء",
            "امر شراء"
        ]

        if any(word in text for word in quotation_words):
            return "Quotation"

        if any(word in text for word in tender_words):
            return "Tender"

        if any(word in text for word in invoice_words):
            return "Invoice"

        if any(word in text for word in purchase_order_words):
            return "Purchase Order"

        return "Unknown"