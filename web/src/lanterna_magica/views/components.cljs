(ns lanterna-magica.views.components
  "Shared, reusable UI components for lanterna-magica."
  (:require [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Search Input
;; ---------------------------------------------------------------------------

(defn search-input
  [{:keys [value on-change placeholder]}]
  [bp/input-group {:left-icon   "search"
                   :placeholder (or placeholder "Search...")
                   :value       (or value "")
                   :on-change   #(on-change (.. % -target -value))}])

;; ---------------------------------------------------------------------------
;; Archive Toggle
;; ---------------------------------------------------------------------------

(defn archive-toggle
  [{:keys [checked on-change]}]
  [bp/switch-control {:checked   (boolean checked)
                      :label     "Archived"
                      :class     "mb-0"
                      :on-change (fn [_] (on-change))}])

;; ---------------------------------------------------------------------------
;; Search + Archive Bar
;; ---------------------------------------------------------------------------

(defn search-bar
  [{:keys [search on-search-change show-archived on-toggle-archived placeholder]}]
  [:div {:class "flex items-center gap-3 mb-4"}
   [:div.flex-1
    [search-input {:value       search
                   :on-change   on-search-change
                   :placeholder placeholder}]]
   [archive-toggle {:checked   show-archived
                    :on-change on-toggle-archived}]])

;; ---------------------------------------------------------------------------
;; Pagination - Load More
;; ---------------------------------------------------------------------------

(defn load-more-button
  [{:keys [has-next? loading? on-click]}]
  (when has-next?
    [:div.text-center.mt-2
     [bp/button {:text     "Load more"
                 :minimal  true
                 :loading  loading?
                 :on-click on-click}]]))

;; ---------------------------------------------------------------------------
;; Page Header
;; ---------------------------------------------------------------------------

(defn page-header
  [{:keys [title loading? on-refresh on-create]}]
  [:div.flex.items-center.justify-between.mb-4
   [:h3.bp6-heading title]
   [:div.flex.items-center.gap-2
    (when on-create
      [bp/button {:icon     "plus"
                  :intent   "primary"
                  :minimal  true
                  :on-click on-create}])
    [bp/button {:icon     "refresh"
                :minimal  true
                :loading  loading?
                :on-click on-refresh}]]])

;; ---------------------------------------------------------------------------
;; Entity Card
;; ---------------------------------------------------------------------------

(defn entity-card
  [{:keys [name description archived? on-click badges]}]
  [:div {:class    (str "mb-2 rounded p-3 cursor-pointer transition-all "
                        "bg-tn-bg-card hover:brightness-110"
                        (when archived? " opacity-60"))
         :on-click on-click}
   [:div.flex.items-center.justify-between
    [:div.flex.items-center.gap-2
     [:span {:class (str "font-semibold" (when archived? " line-through"))} name]
     (when archived?
       [bp/tag {:minimal true :class "ml-2"} "archived"])
     (when badges
       (into [:<>] badges))]
    [bp/icon {:icon "chevron-right" :class "opacity-50"}]]
   (when (seq description)
     [:p {:class "text-sm opacity-60 mt-1 mb-0"} description])])

;; ---------------------------------------------------------------------------
;; Error Banner
;; ---------------------------------------------------------------------------

(defn error-banner [message]
  (when message
    [bp/callout {:intent "danger" :class "mb-4" :icon "error"}
     message]))

;; ---------------------------------------------------------------------------
;; Loading / Empty States
;; ---------------------------------------------------------------------------

(defn loading-spinner []
  [:div.py-8.text-center [bp/spinner {:size 40}]])

(defn empty-state
  [{:keys [icon title description]}]
  [bp/non-ideal-state {:icon        icon
                       :title       title
                       :description description}])
