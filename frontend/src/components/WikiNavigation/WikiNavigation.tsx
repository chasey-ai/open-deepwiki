"use client"; 

import React from 'react';
import Link from 'next/link';
// import { usePathname } from 'next/navigation'; // For active link highlighting (optional for now)

export interface NavItemStructure {
  id: string; // Unique ID for the item, also used for constructing href if relative
  title: string;
  href?: string; // Relative path (e.g., '#section-id' or 'sub-page') or absolute path
  level?: number; // For indentation, not strictly enforced by this component's rendering
  children?: NavItemStructure[];
  isHeader?: boolean; // If true, renders as a non-clickable header
}

interface WikiNavigationProps {
  basePath: string; // e.g., /wiki/owner/repo
  navigationData?: NavItemStructure[]; // Fetched from backend or statically defined
}

// Sample data for example repositories
const sampleNavigationData: NavItemStructure[] = [
  { id: "overview", title: "概述", href: "#overview", level: 1 },
  { id: "installation", title: "安装", level: 1, isHeader: true, children: [
    { id: "requirements", title: "系统要求", href: "#requirements", level: 2 },
    { id: "steps", title: "安装步骤", href: "#steps", level: 2 },
  ]},
  { id: "usage", title: "使用方法", href: "#usage", level: 1 },
  { id: "api", title: "API 参考", href: "api-reference", level: 1, children: [ // Example of linking to a sub-page
      { id: "api-endpoints", title: "端点", href: "api-reference#endpoints", level: 2},
  ]},
  { id: "contributing", title: "贡献", href: "/contributing", level: 1}, // Example of an absolute path
];


const WikiNavigation: React.FC<WikiNavigationProps> = ({ basePath, navigationData }) => {
  const navItems = navigationData && navigationData.length > 0 ? navigationData : sampleNavigationData;
  // const pathname = usePathname(); // For active link highlighting

  const renderNavItems = (items: NavItemStructure[], currentLevel: number = 1): JSX.Element[] => {
    return items.map((item) => {
      let itemHref: string | undefined = undefined;
      if (item.href) {
        if (item.href.startsWith('/') || item.href.startsWith('http')) {
          itemHref = item.href; // Absolute path
        } else if (item.href.startsWith('#')) {
          itemHref = `${basePath}${item.href}`; // Anchor link on the base path
        } else {
          itemHref = `${basePath}/${item.href.replace(/^#/, '')}`; // Relative sub-page or anchor
        }
      }
      
      // const isActive = pathname === itemHref; // Basic active link check

      return (
        <li key={item.id} className={`my-0.5 ${currentLevel > 1 ? 'ml-4' : ''}`}>
          {item.isHeader || !itemHref ? (
            <span 
              className={`block py-1 text-sm font-semibold text-gray-500 ${currentLevel === 1 ? 'mt-2' : 'mt-1'}`}
            >
              {item.title}
            </span>
          ) : (
            <Link href={itemHref} legacyBehavior>
              <a 
                className={`block py-1 text-sm text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-md px-2
                           transition-colors duration-150 ease-in-out
                           ${currentLevel === 1 ? 'font-medium' : ''}
                           `}
                           // ${isActive ? 'text-blue-600 font-bold bg-blue-100' : ''} // Active link styling
              >
                {item.title}
              </a>
            </Link>
          )}
          {item.children && item.children.length > 0 && (
            <ul className="pl-2 border-l border-gray-200">
              {renderNavItems(item.children, currentLevel + 1)}
            </ul>
          )}
        </li>
      );
    });
  };

  if (!navItems || navItems.length === 0) {
    return <p className="text-sm text-gray-500">导航信息加载中或不可用...</p>;
  }

  return (
    <nav aria-label="Wiki Navigation" className="space-y-1">
      <ul>
        {renderNavItems(navItems)}
      </ul>
    </nav>
  );
};

export default WikiNavigation;
