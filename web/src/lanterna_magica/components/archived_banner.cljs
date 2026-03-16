(ns lanterna-magica.components.archived-banner
  "Warning banner for archived entities shown in edit dialogs."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Archived Banner
;; ---------------------------------------------------------------------------

(defn archived-banner
  "Show a warning banner when an entity is archived.
   Pass a message string describing what is archived, e.g. \"This dimension is archived.\""
  [message]
  [:div {:class "mb-4 p-3 rounded bg-tn-orange/10 text-tn-orange text-sm flex items-center gap-2"}
   [bp/icon {:icon "warning-sign" :size 14}]
   message])
