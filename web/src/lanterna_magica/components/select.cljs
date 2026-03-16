(ns lanterna-magica.components.select
  "Searchable dropdown select built on Blueprint Select + lodash debounce."
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.components.debounce :as deb]
   [re-frame.core :as rf]
   [reagent.core :as r]))

(defn searchable-select
  "A searchable dropdown backed by server-side search with debounce.

   Props:
     :items           - vector of items (each with :id and :name)
     :selected-id     - currently selected item id (or nil/\"\")
     :on-select       - (fn [id]) called when user picks an item
     :on-clear        - (fn []) called when user clears selection (optional)
     :on-query-change - re-frame event vector dispatched with query string
     :on-clear-search - re-frame event vector dispatched when query is cleared
     :placeholder     - button text when nothing selected
     :no-results-text - text shown when items is empty
     :fill            - whether to fill parent width (default true)
     :icon            - icon for the trigger button (default nil)"
  [{:keys [items selected-id on-select on-clear on-query-change on-clear-search
           placeholder no-results-text fill icon]}]
  (r/with-let [debounced-search (deb/make-debounced-fn
                                  (fn [query] (rf/dispatch (conj on-query-change query))))]
    (let [items    (or items [])
          selected (some #(when (= (:id %) selected-id) %) items)
          fill?    (if (some? fill) fill true)]

      [:> bp/select-component
       {:items             (clj->js items)
        :fill              fill?
        :item-renderer     (fn [item props]
                             (let [item (js->clj item :keywordize-keys true)]
                               (r/as-element
                                 [bp/menu-item
                                  {:key      (:id item)
                                   :text     (:name item)
                                   :on-click (.-handleClick props)
                                   :active   (.. props -modifiers -active)
                                   :role-structure "listoption"}])))
        :on-item-select    (fn [item]
                             (let [item (js->clj item :keywordize-keys true)]
                               (on-select (:id item))))
        :on-query-change   (fn [query]
                             (if (seq query)
                               (@debounced-search query)
                               (do
                                 (deb/cancel-debounced-fn! debounced-search)
                                 (rf/dispatch on-clear-search))))
        :items-equal       "id"
        :no-results        (r/as-element
                             [bp/menu-item {:disabled true
                                            :text     (or no-results-text "No results.")
                                            :role-structure "listoption"}])
        :popover-props     {:minimal   true
                            :match-target-width fill?}
        :reset-on-close    true
        :filterable        true
        :input-props       {:placeholder "Search..."}
        ;; Disable client-side filtering — we filter server-side
        :item-list-predicate (fn [_query items] items)}

       (if (and on-clear selected)
         [:div.flex.items-center.gap-0 {:class (when fill? "w-full")}
          [bp/button {:text       (:name selected)
                      :right-icon "caret-down"
                      :icon       icon
                      :fill       fill?
                      :align-text "left"
                      :class      "flex-1"}]
          [bp/button {:icon     "small-cross"
                      :minimal  true
                      :small    true
                      :on-click (fn [e]
                                  (.stopPropagation e)
                                  (on-clear))}]]
         [bp/button {:text       (or (:name selected) placeholder "Select...")
                     :right-icon "caret-down"
                     :icon       icon
                     :fill       fill?
                     :align-text "left"}])])
    (finally
      (deb/cancel-debounced-fn! debounced-search))))
